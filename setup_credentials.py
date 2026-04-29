import sys
import getpass
import keyring

SERVICE_NAME = "smtp_cli"


def main() -> int:
    email = input("Enter the email address you want to send the email from: ").strip()
    password = getpass.getpass(
        "Enter your SMTP password (or app password if using Gmail): "
    ).strip()

    if not email or not password:
        print("ERROR: email and password are both required.")
        return 1

    keyring.set_password(SERVICE_NAME, "sender_email", email)
    keyring.set_password(SERVICE_NAME, "sender_password", password)

    print("Credentials have been securely stored in the keyring.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
