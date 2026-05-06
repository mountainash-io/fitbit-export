from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import time
import webbrowser
from dataclasses import dataclass
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qs

import httpx

DEFAULT_CLIENT_ID = os.environ.get("FITBIT_CLIENT_ID", "22C4DT")
DEFAULT_CLIENT_SECRET = os.environ.get("FITBIT_CLIENT_SECRET", "30ce443dcc6181dc6b422d90cb4b8218")

TOKEN_DIR = Path("~/.fitbit-export").expanduser()

AUTHORIZE_URL = "https://www.fitbit.com/oauth2/authorize"
TOKEN_URL = "https://api.fitbit.com/oauth2/token"
PROFILE_URL = "https://api.fitbit.com/1/user/-/profile.json"
CALLBACK_PORT = 8080
SCOPE = "activity heartrate location nutrition oxygen_saturation profile respiratory_rate settings sleep social temperature weight"


@dataclass
class AuthenticatedUser:
    user_id: str
    display_name: str
    client: httpx.Client


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        self.server._callback_params = {k: v[0] for k, v in params.items()}
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html><body><h1>Authorization complete!</h1>"
                         b"<p>You can close this window and return to the terminal.</p></body></html>")

    def log_message(self, format, *args) -> None:
        pass


def _wait_for_callback() -> dict[str, str]:
    server = HTTPServer(("localhost", CALLBACK_PORT), _CallbackHandler)
    server._callback_params = None
    server.timeout = 120
    server.handle_request()
    if server._callback_params is None:
        raise TimeoutError("No OAuth callback received within 2 minutes")
    try:
        return server._callback_params
    finally:
        server.server_close()


def _build_pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge


def _run_oauth_flow(client_id: str, client_secret: str) -> dict:
    verifier, challenge = _build_pkce()
    state = secrets.token_urlsafe(32)
    redirect_uri = f"http://localhost:{CALLBACK_PORT}/callback"

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "state": state,
        "scope": SCOPE,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    url = f"{AUTHORIZE_URL}?{urlencode(params)}"

    print(f"Opening browser for Fitbit authorization...")
    print(f"If the browser doesn't open, visit: {url}")
    webbrowser.open(url)

    callback_params = _wait_for_callback()

    if callback_params.get("state") != state:
        raise ValueError("OAuth state mismatch")

    with httpx.Client() as http:
        resp = http.post(TOKEN_URL, data={
            "grant_type": "authorization_code",
            "code": callback_params["code"],
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
            "code_verifier": verifier,
        })
        resp.raise_for_status()
        token_data = resp.json()

    expires_at = None
    if "expires_in" in token_data:
        expires_at = int(time.time()) + int(token_data["expires_in"])

    return {
        "access_token": token_data["access_token"],
        "refresh_token": token_data.get("refresh_token", ""),
        "token_expires_at": expires_at,
    }


def _refresh_tokens(refresh_token: str, client_id: str, client_secret: str) -> dict:
    with httpx.Client() as http:
        resp = http.post(TOKEN_URL, data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        })
        resp.raise_for_status()
        token_data = resp.json()

    expires_at = None
    if "expires_in" in token_data:
        expires_at = int(time.time()) + int(token_data["expires_in"])

    return {
        "access_token": token_data["access_token"],
        "refresh_token": token_data.get("refresh_token", refresh_token),
        "token_expires_at": expires_at,
    }


def _is_expired(expires_at: int | None) -> bool:
    if expires_at is None:
        return False
    return time.time() >= (expires_at - 300)


def _token_path(token_dir: Path, user_id: str) -> Path:
    return token_dir / f"tokens-{user_id}.json"


def _save_tokens(token_dir: Path, user_id: str, display_name: str, tokens: dict) -> None:
    token_dir.mkdir(parents=True, exist_ok=True)
    data = {
        **tokens,
        "user_id": user_id,
        "display_name": display_name,
    }
    path = _token_path(token_dir, user_id)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _load_tokens(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _make_client(access_token: str) -> httpx.Client:
    return httpx.Client(
        base_url="https://api.fitbit.com",
        headers={"Authorization": f"Bearer {access_token}"},
    )


def _fetch_profile(client: httpx.Client) -> tuple[str, str]:
    resp = client.get("/1/user/-/profile.json")
    resp.raise_for_status()
    user = resp.json()["user"]
    return user["encodedId"], user.get("fullName", user.get("displayName", "Unknown"))


class FitbitAuth:
    def __init__(
        self,
        client_id: str = DEFAULT_CLIENT_ID,
        client_secret: str = DEFAULT_CLIENT_SECRET,
        token_dir: Path = TOKEN_DIR,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._token_dir = token_dir

    def add_user(self) -> AuthenticatedUser:
        tokens = _run_oauth_flow(self._client_id, self._client_secret)
        client = _make_client(tokens["access_token"])
        user_id, display_name = _fetch_profile(client)
        _save_tokens(self._token_dir, user_id, display_name, tokens)
        print(f"Authenticated: {display_name} ({user_id})")
        return AuthenticatedUser(user_id=user_id, display_name=display_name, client=client)

    def authenticate(self, user_id: str) -> AuthenticatedUser:
        path = _token_path(self._token_dir, user_id)
        tokens = _load_tokens(path)
        if tokens is None:
            raise ValueError(f"No tokens found for user {user_id}")

        if _is_expired(tokens.get("token_expires_at")):
            tokens = _refresh_tokens(
                tokens["refresh_token"], self._client_id, self._client_secret,
            )
            _save_tokens(
                self._token_dir, user_id,
                tokens.get("display_name", "Unknown"), tokens,
            )

        client = _make_client(tokens["access_token"])
        display_name = tokens.get("display_name", "Unknown")
        return AuthenticatedUser(user_id=user_id, display_name=display_name, client=client)

    def list_users(self) -> list[dict]:
        users = []
        for path in sorted(self._token_dir.glob("tokens-*.json")):
            tokens = _load_tokens(path)
            if tokens:
                users.append({
                    "user_id": tokens.get("user_id", ""),
                    "display_name": tokens.get("display_name", "Unknown"),
                })
        return users

    def authenticate_all(self) -> list[AuthenticatedUser]:
        users = self.list_users()
        if not users:
            return [self.add_user()]
        return [self.authenticate(u["user_id"]) for u in users]
