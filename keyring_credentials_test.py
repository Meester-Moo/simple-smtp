import keyring

SERVICE_NAME = "smtp_cli"

email = keyring.get_password(SERVICE_NAME, "sender_email")
password = keyring.get_password(SERVICE_NAME, "sender_password")

if not email and not password:
    print("No credentials found. Run setup_credentials.py first.")
    exit(1)
elif not email:
    print("Email is missing from keyring. Run setup_credentials.py to add it.")
    exit(1)
elif not password:
    print("Password is missing from keyring. Run setup_credentials.py to add it.")
    exit(1)


print("Email retrieved:", email)

print(
    "SMTP password (or app password if using Gmail) retrieved from keyring:", password
)
