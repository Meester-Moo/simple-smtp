import keyring
import getpass

SERVICE_NAME = "smtp_cli"  # Service name for keyring storage

# Prompt the user for email and password, then store them in the keyring
email = input("Enter the email address you want to send the email from: ").strip()

password = getpass.getpass(
    "Enter your SMTP password (or app password if using Gmail): "
).strip()

keyring.set_password(SERVICE_NAME, "sender_email", email)
keyring.set_password(SERVICE_NAME, "sender_password", password)

print("Credentials have been securely stored in the keyring.")
