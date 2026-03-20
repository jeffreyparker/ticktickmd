"""OAuth 2.0 authentication for TickTick API."""

import json
import os
import secrets
import sys
import time
import webbrowser
from getpass import getpass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse

from .exceptions import AuthError, TokenExpiredError


AUTHORIZE_URL = "https://ticktick.com/oauth/authorize"
TOKEN_URL = "https://ticktick.com/oauth/token"
REDIRECT_URI = "http://localhost:8090/callback"
SCOPE = "tasks:read"
CALLBACK_PORT = 8090


def get_config_dir() -> Path:
    """Get the configuration directory, creating it if needed."""
    config_dir = Path.home() / ".config" / "ticktickmd"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def load_config() -> dict:
    """Load client configuration from config file."""
    config_path = get_config_dir() / "config.json"
    if config_path.exists():
        return json.loads(config_path.read_text())
    return {}


def save_config(config: dict) -> None:
    """Save client configuration to config file."""
    config_path = get_config_dir() / "config.json"
    config_path.write_text(json.dumps(config, indent=2))
    config_path.chmod(0o600)


def load_tokens() -> Optional[dict]:
    """Load stored tokens."""
    token_path = get_config_dir() / "tokens.json"
    if token_path.exists():
        return json.loads(token_path.read_text())
    return None


def save_tokens(tokens: dict) -> None:
    """Save tokens to file with restricted permissions."""
    token_path = get_config_dir() / "tokens.json"
    token_path.write_text(json.dumps(tokens, indent=2))
    token_path.chmod(0o600)


def clear_tokens() -> None:
    """Remove stored tokens."""
    token_path = get_config_dir() / "tokens.json"
    if token_path.exists():
        token_path.unlink()


def get_client_credentials() -> tuple[str, str]:
    """Get client ID and secret from env vars or config file.

    Environment variables take precedence over config file.

    Returns:
        Tuple of (client_id, client_secret)

    Raises:
        AuthError: If credentials are not configured
    """
    client_id = os.environ.get("TICKTICK_CLIENT_ID")
    client_secret = os.environ.get("TICKTICK_CLIENT_SECRET")

    if client_id and client_secret:
        return client_id, client_secret

    config = load_config()
    client_id = client_id or config.get("client_id")
    client_secret = client_secret or config.get("client_secret")

    if not client_id or not client_secret:
        raise AuthError(
            "Client credentials not configured. Run 'ticktickmd auth login' first, "
            "or set TICKTICK_CLIENT_ID and TICKTICK_CLIENT_SECRET environment variables."
        )

    return client_id, client_secret


def get_access_token() -> str:
    """Get a valid access token, refreshing if needed.

    Returns:
        Access token string

    Raises:
        AuthError: If not authenticated
        TokenExpiredError: If token is expired and can't be refreshed
    """
    tokens = load_tokens()
    if not tokens:
        raise AuthError(
            "Not authenticated. Run 'ticktickmd auth login' first."
        )

    # Check if token is expired
    expires_at = tokens.get("expires_at", 0)
    if time.time() < expires_at - 60:  # 60 second buffer
        return tokens["access_token"]

    # Try to refresh
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        raise TokenExpiredError(
            "Access token expired and no refresh token available. "
            "Run 'ticktickmd auth login' again."
        )

    try:
        client_id, client_secret = get_client_credentials()
        new_tokens = _refresh_token(client_id, client_secret, refresh_token)
        save_tokens(new_tokens)
        return new_tokens["access_token"]
    except Exception as e:
        raise TokenExpiredError(
            f"Failed to refresh token: {e}. Run 'ticktickmd auth login' again."
        )


def _refresh_token(client_id: str, client_secret: str, refresh_token: str) -> dict:
    """Refresh an expired access token."""
    try:
        import httpx
    except ImportError:
        raise AuthError("httpx is required for API access. Install with: pip install ticktickmd[api]")

    response = httpx.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        auth=(client_id, client_secret),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    if response.status_code != 200:
        raise AuthError(f"Token refresh failed: {response.status_code} {response.text}")

    data = response.json()
    data["expires_at"] = time.time() + data.get("expires_in", 3600)
    return data


def start_auth_flow(client_id: str, client_secret: str) -> dict:
    """Run the OAuth 2.0 authorization code flow.

    Opens a browser for the user to authorize, then exchanges the
    authorization code for tokens.

    Returns:
        Token dict with access_token, refresh_token, expires_at
    """
    try:
        import httpx
    except ImportError:
        raise AuthError("httpx is required for API access. Install with: pip install ticktickmd[api]")

    state = secrets.token_urlsafe(32)
    auth_code = None
    error_message = None

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal auth_code, error_message
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)

            if params.get("state", [None])[0] != state:
                error_message = "State mismatch — possible CSRF attack"
                self.send_response(400)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h1>Error: State mismatch</h1>")
                return

            if "error" in params:
                error_message = params["error"][0]
                self.send_response(400)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(f"<h1>Error: {error_message}</h1>".encode())
                return

            auth_code = params.get("code", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<h1>Authorization successful!</h1>"
                b"<p>You can close this tab and return to the terminal.</p>"
            )

        def log_message(self, format, *args):
            pass  # Suppress server logs

    # Build authorization URL
    params = urlencode({
        "client_id": client_id,
        "scope": SCOPE,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "state": state,
    })
    auth_url = f"{AUTHORIZE_URL}?{params}"

    print(f"\nOpening browser for authorization...")
    print(f"If the browser doesn't open, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)

    # Start callback server
    server = HTTPServer(("localhost", CALLBACK_PORT), CallbackHandler)
    server.timeout = 300  # 5 minute timeout
    print("Waiting for authorization callback...")

    while auth_code is None and error_message is None:
        server.handle_request()

    server.server_close()

    if error_message:
        raise AuthError(f"Authorization failed: {error_message}")

    if not auth_code:
        raise AuthError("No authorization code received")

    # Exchange code for tokens
    print("Exchanging authorization code for tokens...")
    response = httpx.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": REDIRECT_URI,
        },
        auth=(client_id, client_secret),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    if response.status_code != 200:
        raise AuthError(f"Token exchange failed: {response.status_code} {response.text}")

    tokens = response.json()
    tokens["expires_at"] = time.time() + tokens.get("expires_in", 3600)
    return tokens


def auth_status() -> dict:
    """Get current authentication status.

    Returns:
        Dict with status info (authenticated, token_valid, expires_at, etc.)
    """
    result = {"authenticated": False}

    tokens = load_tokens()
    if not tokens:
        return result

    result["authenticated"] = True
    expires_at = tokens.get("expires_at", 0)
    result["expires_at"] = expires_at
    result["token_valid"] = time.time() < expires_at
    result["has_refresh_token"] = "refresh_token" in tokens

    try:
        get_client_credentials()
        result["credentials_configured"] = True
    except AuthError:
        result["credentials_configured"] = False

    return result


def handle_auth_command(action: str) -> None:
    """Handle auth subcommand actions (login/status/logout)."""
    if action == "login":
        # Prompt for credentials
        config = load_config()
        existing_id = config.get("client_id", "")

        print("TickTick API OAuth Setup")
        print("========================")
        print("You need a TickTick API app. Create one at:")
        print("https://developer.ticktick.com/manage")
        print(f"\nSet the OAuth redirect URL to: {REDIRECT_URI}\n")

        client_id = input(f"Client ID [{existing_id or 'none'}]: ").strip()
        if not client_id:
            client_id = existing_id
        if not client_id:
            print("Error: Client ID is required.", file=sys.stderr)
            sys.exit(1)

        client_secret = getpass("Client Secret: ").strip()
        if not client_secret:
            # Keep existing if available
            existing_secret = config.get("client_secret")
            if existing_secret:
                client_secret = existing_secret
                print("(using previously saved secret)")
            else:
                print("Error: Client Secret is required.", file=sys.stderr)
                sys.exit(1)

        # Save credentials
        save_config({"client_id": client_id, "client_secret": client_secret})
        print("Credentials saved.\n")

        # Start OAuth flow
        try:
            tokens = start_auth_flow(client_id, client_secret)
            save_tokens(tokens)
            print("\nAuthentication successful! Tokens saved.")
        except AuthError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif action == "status":
        status = auth_status()
        if not status["authenticated"]:
            print("Not authenticated. Run 'ticktickmd auth login' to set up.")
            return

        print(f"Authenticated: yes")
        if status["token_valid"]:
            remaining = status["expires_at"] - time.time()
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            print(f"Token valid: yes ({hours}h {minutes}m remaining)")
        else:
            print("Token valid: no (expired)")
        print(f"Refresh token: {'yes' if status['has_refresh_token'] else 'no'}")
        print(f"Credentials configured: {'yes' if status['credentials_configured'] else 'no'}")

    elif action == "logout":
        clear_tokens()
        print("Tokens cleared. You can also remove credentials from:")
        print(f"  {get_config_dir() / 'config.json'}")

    else:
        print(f"Unknown auth action: {action}", file=sys.stderr)
        sys.exit(1)
