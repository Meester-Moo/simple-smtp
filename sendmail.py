import keyring
import argparse
import smtplib
import ssl
from email.message import EmailMessage

SERVICE_NAME = "smtp_cli"


def get_credentials():
    email = keyring.get_password(SERVICE_NAME, "sender_email")
    password = keyring.get_password(SERVICE_NAME, "sender_password")

    if not email and not password:
        print(
            "ERROR: No email and password credentials found for the sender. Run setup_credentials.py first."
        )
        exit(1)
    elif not email:
        print(
            "ERROR: Email is missing from keyring. Run setup_credentials.py to add it."
        )
        exit(1)
    elif not password:
        print(
            "ERROR: Password is missing from keyring. Run setup_credentials.py to add it."
        )
        exit(1)

    return email, password


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple SMTP email sender")

    parser.add_argument("to", help="Recipient email address")
    parser.add_argument("-s", "--subject", default="No Subject", help="Email subject")
    parser.add_argument("-b", "--body", default="No Body", help="Email body")

    args = parser.parse_args()

    email, password = get_credentials()

    print(f"Ready to send email from: {email}")
    print(f"To: {args.to}")
    print(f"Subject: {args.subject}")
    print(
        f"Body: {args.body[:100] + '...' if len(args.body) > 100 else args.body}"
        # Print first 100 chars of body for preview
    )

    msg = EmailMessage()
    msg["From"] = email
    msg["To"] = args.to
    msg["Subject"] = args.subject
    msg.set_content(args.body)

    context = ssl.create_default_context()

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context)
        server.login(email, password)
        server.send_message(msg)

        print("Email sent successfully!")

    except Exception as e:
        print(f"Failed to send email: {e}")
    finally:
        try:
            server.quit()
        except:
            pass
