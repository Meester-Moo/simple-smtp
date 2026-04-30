"""Verifies that credentials are present in the keyring under the
expected service name. Useful as a sanity check after setup_credentials.py,
or to confirm credentials were removed. Never prints the password itself."""

import sys
import keyring

SERVICE_NAME = "smtp_cli"


def main() -> int:
    # keyring.get_password() returns None if no entry exists for that
    # (service, username) pair. None is "falsy" in Python — meaning it
    # behaves as False in boolean contexts — so `if not value` catches
    # both "missing entry" and "stored as empty string" with one check.
    email = keyring.get_password(SERVICE_NAME, "sender_email")
    password = keyring.get_password(SERVICE_NAME, "sender_password")

    # Early-return / "guard clause" pattern: each check is independent
    # and exits the function the moment it fires. Reads top-to-bottom
    # with no nested elif ladders. The pattern is language-neutral —
    # the same instinct that says "fail fast, then proceed" instead of
    # building deep nested `if/else` blocks.
    if not email and not password:
        print("No credentials found. Run setup_credentials.py first.")
        return 1
    if not email:
        print("Email is missing from keyring. Run setup_credentials.py to add it.")
        return 1
    if not password:
        print("Password is missing from keyring. Run setup_credentials.py to add it.")
        return 1

    # Confirm presence WITHOUT echoing the value. A "secret store" that
    # prints the secret to stdout is not actually a secret store — anyone
    # with eyes on the terminal (or a screen-share, or a recorded session,
    # or a captured log file) would see the password. Same defense-in-
    # depth principle that says service-account passwords should never
    # appear in script output, log files, or error messages.
    print(f"Email retrieved: {email}")
    print("Password is present in keyring (hidden).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
