"""Create the two test logins listed in the README, through the app's normal sign-up.

Nobody is pre-registered in the data: this just signs two people up for you, so a
reviewer can log in straight away. Run it while the app is running:

    .venv/bin/python scripts/create_test_accounts.py [--base http://127.0.0.1:8000]

Safe to run more than once.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request

# Test-only passwords for this exercise. Never reuse a real password here.
TEST_ACCOUNTS = [
    ("dana.whitfield@brightline.example", "frontdesk-admin", "admin"),
    ("sam.ferreira@brightline.example", "frontdesk-viewer", "viewer"),
]


def sign_up(base: str, email: str, password: str) -> int:
    request = urllib.request.Request(
        f"{base}/api/auth/signup",
        data=json.dumps({"email": email, "password": password}).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status
    except urllib.error.HTTPError as e:
        return e.code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="http://127.0.0.1:8000", help="where the app is running")
    base = parser.parse_args().base.rstrip("/")
    for email, password, role in TEST_ACCOUNTS:
        try:
            status = sign_up(base, email, password)
        except (urllib.error.URLError, OSError):
            print(f"Can't reach the app at {base}. Start it first: .venv/bin/uvicorn app.main:app")
            return 1
        if status == 201:
            print(f"Created {role} login {email}")
        elif status == 409:
            print(f"Already exists: {email}")
        else:
            print(f"Couldn't create {email} (HTTP {status})")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
