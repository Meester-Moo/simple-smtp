import sys
import keyring

SERVICE_NAME = "smtp_cli"


def main() -> int:
    email = keyring.get_password(SERVICE_NAME, "sender_email")
    password = keyring.get_password(SERVICE_NAME, "sender_password")

    if not email and not password:
        print("No credentials found. Run setup_credentials.py first.")
        return 1
    if not email:
        print("Email is missing from keyring. Run setup_credentials.py to add it.")
        return 1
    if not password:
        print("Password is missing from keyring. Run setup_credentials.py to add it.")
        return 1

    # Never print the password itself — that defeats the point of using a secret store.
    print(f"Email retrieved: {email}")
    print("Password is present in keyring (hidden).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
