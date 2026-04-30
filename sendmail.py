"""CLI for sending one email over SMTP using credentials pulled from
the OS keyring. Picks the right TLS mode based on the port: 465 uses
implicit TLS (SMTPS), anything else uses STARTTLS to upgrade a plaintext
SMTP session to TLS before authenticating."""

import sys
import re
import socket       # only used to catch the DNS-resolution exception below
import argparse
import smtplib
import ssl
from email.message import EmailMessage

# Third-party imports go after stdlib, separated by a blank line (PEP 8).
import keyring

SERVICE_NAME = "smtp_cli"

# Pre-compiling the regex once at import time is a small optimization:
# `re.match(pattern, ...)` would compile the pattern on every call.
#
# The pattern is intentionally permissive — fully validating an RFC 5322
# email address with a regex is famously hard (quoted local parts, comments,
# IP literals, internationalized domains...). This catches obvious typos
# before we open a TCP socket; the SMTP server does the real validation
# when we actually try to send.
EMAIL_RE = re.compile(r"[^@]+@[^@]+\.[^@]+")


# `-> tuple[str, str]` is a *type hint* — it documents that this function
# returns a pair of strings. Python doesn't enforce hints at runtime; tools
# like mypy / Pyright verify them statically. If you've seen TypeScript,
# the idea is identical: the annotations are for tooling and humans, and
# the code runs the same with or without them.
def get_credentials() -> tuple[str, str]:
    """Pull the sender email + password from the OS keyring. Exits the
    process with code 1 if either is missing — there's nothing this CLI
    can do without both, so failing loudly here keeps main() simple."""
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

    # Returning two values: Python implicitly packs them into a tuple, and
    # the caller unpacks with `email, password = get_credentials()`. Same
    # idea as JavaScript array destructuring — `const [a, b] = getPair();`.
    return email, password


def parse_args() -> argparse.Namespace:
    """Defines the CLI surface. Kept separate from main() so the argument
    declarations are easy to scan without hunting through business logic.
    `argparse` is Python's stdlib library for declaring CLI arguments —
    it generates the `--help` text automatically, validates types, and
    returns a populated `Namespace` object holding the parsed values."""
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
        type=int,  # converts the CLI string to int automatically
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

    There are two TLS modes for SMTP submission, picked here by port —
    same protocol either way, different handshake sequence:

    Port 465 (SMTPS / implicit TLS):
        TCP handshake -> TLS handshake -> SMTP commands.
        TLS is negotiated before any SMTP greeting is exchanged. There's
        never a moment where credentials could leak in plaintext, because
        the connection is encrypted before SMTP even starts speaking.

    Anything else (typically 587, the "submission" port — STARTTLS):
        TCP handshake -> plaintext SMTP greeting (EHLO) -> client issues
        STARTTLS -> TLS handshake -> EHLO again -> AUTH + send.

        The client MUST issue STARTTLS before sending credentials. If the
        client forgets — or an attacker downgrades the session via a
        STARTTLS-stripping MITM — the password leaves in cleartext. This
        is exactly the kind of misconfiguration EDR/SIEM tools watch for,
        and it's why modern submission flows are increasingly favoring 465.

    Why two EHLOs?
        The SMTP server's advertised capabilities (e.g. supported AUTH
        mechanisms) can change after TLS is negotiated — most servers
        only advertise AUTH PLAIN/LOGIN once the channel is encrypted.
        Re-greeting refreshes the capability list.
    """
    # ssl.create_default_context() returns an SSLContext with sane,
    # security-focused defaults: verifies the server's certificate against
    # the system trust store (the same root CA bundle the OS uses for
    # browsers), requires TLS 1.2 or higher, and enables hostname
    # verification. Don't reach for the lower-level ssl primitives unless
    # you have a specific reason — the defaults here are what you want.
    context = ssl.create_default_context()

    # `with` is Python's context-manager protocol. It guarantees that
    # cleanup code runs when the block exits — whether the block ends
    # normally OR an exception is raised inside it. The smtplib classes
    # implement the protocol, so `server.quit()` is called automatically
    # at the end of the `with`. Same job as a `try / finally` block, just
    # baked into the language so you can't forget the cleanup step.
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as server:
            server.login(username, password)
            server.send_message(msg)
    else:
        # Plaintext-then-upgrade flow (STARTTLS). Each call below maps
        # almost 1:1 to a wire-level command you'd see in a packet capture
        # — useful to step through if you ever capture this in Wireshark.
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.ehlo()                       # EHLO mail.example.com  (plaintext)
            server.starttls(context=context)    # STARTTLS, then TLS handshake
            server.ehlo()                       # EHLO again — capabilities can differ post-TLS
            server.login(username, password)    # AUTH (now safe on the encrypted channel)
            server.send_message(msg)            # MAIL FROM / RCPT TO / DATA


def main() -> int:
    args = parse_args()

    # Cheap local validation first — no point opening a network socket if
    # the recipient is obviously malformed. Cheap to fail here; expensive
    # to fail after a TCP+TLS handshake.
    if not EMAIL_RE.match(args.to):
        print(f"ERROR: '{args.to}' is not a valid email address.")
        return 1

    email, password = get_credentials()

    # Truncate the body for the on-screen preview so we don't spam the
    # terminal if a long message gets passed in. f-strings (the f"...{var}..."
    # syntax) are Python's interpolated strings — same idea as JavaScript
    # template literals: `Hello ${name}`.
    body_preview = args.body[:100] + "..." if len(args.body) > 100 else args.body
    print(f"Ready to send email from: {email}")
    print(f"To: {args.to}")
    print(f"Subject: {args.subject}")
    print(f"Body: {body_preview}")

    # EmailMessage builds the RFC 5322 message: it sets the proper headers,
    # picks a Content-Type, encodes the body, generates a Message-ID, etc.
    #
    # SECURITY: building these by hand (string-concatenating headers and
    # body) is how header-injection bugs sneak in — if attacker-controlled
    # input contains a CRLF, they can inject extra headers like Bcc: or
    # Subject:, hijacking the message. Always use a proper email-builder
    # library; never f-string headers together yourself.
    msg = EmailMessage()
    msg["From"] = email
    msg["To"] = args.to
    msg["Subject"] = args.subject
    msg.set_content(args.body)

    # Specific exception handling — each `except` clause maps to a distinct
    # failure layer of the stack. Same diagnostic instinct you'd use
    # triaging any incident ticket: is this an *auth* problem, a *transport*
    # problem, or a *DNS* problem? Catching `Exception` blanket-style
    # would collapse all of these into one unhelpful "Failed to send".
    try:
        send(msg, args.smtp_host, args.smtp_port, email, password)
    except smtplib.SMTPAuthenticationError as e:
        # Server returned a 5xx auth failure (typically 535 on Gmail).
        # Most common cause for Gmail: the user gave their account password
        # instead of an App Password. Google blocks regular passwords from
        # SMTP login when 2FA is enabled, which is the default state now.
        print(
            f"ERROR: Authentication failed ({e.smtp_code}): {e.smtp_error.decode(errors='replace')}"
        )
        print(
            "If using Gmail, make sure you generated an App Password and used that — not your regular account password."
        )
        return 1
    except smtplib.SMTPRecipientsRefused as e:
        # Server accepted login but refused the RCPT TO command. Could be
        # a denylist, a non-existent mailbox, or a domain the server won't
        # relay to. The exception's `.recipients` is a dict of {address: (code, msg)}.
        print(f"ERROR: Server refused recipient(s): {e.recipients}")
        return 1
    except smtplib.SMTPConnectError as e:
        # Couldn't establish a usable SMTP session even though the TCP+TLS
        # connection itself came up — e.g. the server immediately rejected
        # us with a 4xx/5xx greeting.
        print(f"ERROR: Could not connect to {args.smtp_host}:{args.smtp_port} ({e})")
        return 1
    except smtplib.SMTPException as e:
        # Catch-all for any other SMTP-level error — e.g. the server
        # returns a weird response code mid-transaction.
        print(f"ERROR: SMTP error: {e}")
        return 1
    except socket.gaierror as e:
        # "getaddrinfo error" — DNS failed to resolve the SMTP host to an
        # IP address. This is the layer the CCNA covers under name
        # resolution / DNS troubleshooting. Equivalent of running
        # `nslookup smtp.gmail.com` and getting no result.
        print(
            f"ERROR: Could not resolve hostname '{args.smtp_host}' (DNS failure): {e}"
        )
        return 1
    except (ConnectionRefusedError, TimeoutError, OSError) as e:
        # TCP/network-layer issues: TCP RST (port closed or firewall drop),
        # no route to host, or socket timeout. The same set of failures
        # you'd diagnose with `telnet smtp.gmail.com 465`, `tracert`, or a
        # packet capture in Wireshark.
        print(f"ERROR: Network error talking to {args.smtp_host}:{args.smtp_port}: {e}")
        return 1

    print("Email sent successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
