import sys
import re
import socket
import argparse
import smtplib
import ssl
from email.message import EmailMessage

import keyring

SERVICE_NAME = "smtp_cli"

# Loose check — RFC 5322 addresses are far more complex, but this is good enough
# to catch obvious typos before opening a network connection.
EMAIL_RE = re.compile(r"[^@]+@[^@]+\.[^@]+")


def get_credentials() -> tuple[str, str]:
    email = keyring.get_password(SERVICE_NAME, "sender_email")
    password = keyring.get_password(SERVICE_NAME, "sender_password")

    if not email and not password:
        print(
            "ERROR: No credentials found for the sender. "
            "Run setup_credentials.py first."
        )
        sys.exit(1)
    if not email:
        print(
            "ERROR: Email is missing from keyring. Run setup_credentials.py to add it."
        )
        sys.exit(1)
    if not password:
        print(
            "ERROR: Password is missing from keyring. Run setup_credentials.py to add it."
        )
        sys.exit(1)

    return email, password


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simple SMTP email sender")
    parser.add_argument("-t", "--to", required=True, help="Recipient email address")
    parser.add_argument("-s", "--subject", default="No Subject", help="Email subject")
    parser.add_argument("-b", "--body", default="No Body", help="Email body")
    parser.add_argument(
        "--smtp-host",
        default="smtp.gmail.com",
        help="SMTP server hostname (default: smtp.gmail.com)",
    )
    parser.add_argument(
        "--smtp-port",
        type=int,
        default=465,
        help="SMTP server port. 465 = implicit TLS (SMTPS); 587 = STARTTLS (default: 465)",
    )
    return parser.parse_args()


def send(
    msg: EmailMessage,
    host: str,
    port: int,
    username: str,
    password: str,
) -> None:
    """Connect to the SMTP server and send the message.

    Port 465 uses implicit TLS from the moment the socket opens (SMTPS).
    Any other port (typically 587) uses STARTTLS — the connection starts in
    plaintext and is upgraded to TLS via the STARTTLS command before auth.
    """
    context = ssl.create_default_context()

    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as server:
            server.login(username, password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(username, password)
            server.send_message(msg)


def main() -> int:
    args = parse_args()

    if not EMAIL_RE.match(args.to):
        print(f"ERROR: '{args.to}' is not a valid email address.")
        return 1

    email, password = get_credentials()

    body_preview = args.body[:100] + "..." if len(args.body) > 100 else args.body
    print(f"Ready to send email from: {email}")
    print(f"To: {args.to}")
    print(f"Subject: {args.subject}")
    print(f"Body: {body_preview}")

    msg = EmailMessage()
    msg["From"] = email
    msg["To"] = args.to
    msg["Subject"] = args.subject
    msg.set_content(args.body)

    try:
        send(msg, args.smtp_host, args.smtp_port, email, password)
    except smtplib.SMTPAuthenticationError as e:
        print(
            f"ERROR: Authentication failed ({e.smtp_code}): {e.smtp_error.decode(errors='replace')}"
        )
        print(
            "If using Gmail, make sure you generated an App Password and used that — not your regular account password."
        )
        return 1
    except smtplib.SMTPRecipientsRefused as e:
        print(f"ERROR: Server refused recipient(s): {e.recipients}")
        return 1
    except smtplib.SMTPConnectError as e:
        print(f"ERROR: Could not connect to {args.smtp_host}:{args.smtp_port} ({e})")
        return 1
    except smtplib.SMTPException as e:
        print(f"ERROR: SMTP error: {e}")
        return 1
    except socket.gaierror as e:
        print(
            f"ERROR: Could not resolve hostname '{args.smtp_host}' (DNS failure): {e}"
        )
        return 1
    except (ConnectionRefusedError, TimeoutError, OSError) as e:
        print(f"ERROR: Network error talking to {args.smtp_host}:{args.smtp_port}: {e}")
        return 1

    print("Email sent successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
