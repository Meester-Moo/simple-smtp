"""Stores the sender's SMTP credentials in the OS keyring so the other
scripts in this project can look them up later without prompting or
reading any plaintext file. Run this once, before sendmail.py."""

import sys

# PEP 8 import grouping: stdlib first, blank line, then third-party.
# `keyring` is the only third-party package — see requirements.txt.
import getpass
import keyring

# Composite-key namespace for keyring entries. Without this, our values
# would collide with every other tool on this machine that uses keyring.
# Conceptually similar to a "vault folder" or "credential category" in
# a password manager — it scopes the (username -> secret) lookup.
SERVICE_NAME = "smtp_cli"


def main() -> int:
    # input() reads a line from stdin and echoes it. Fine for a non-secret.
    email = input("Enter the email address you want to send the email from: ").strip()

    # getpass.getpass() reads a line *without* echoing characters — same
    # idea as PowerShell's `Read-Host -AsSecureString`, minus the
    # SecureString wrapper. Also avoids putting the password in shell
    # history if someone wraps the script call in a longer command.
    password = getpass.getpass(
        "Enter your SMTP password (or app password if using Gmail): "
    ).strip()

    # Validate at the trust boundary. If the user just hits Enter, empty
    # strings would silently land in the keyring and only surface later
    # as a confusing auth failure when sendmail.py tries to log in.
    if not email or not password:
        print("ERROR: email and password are both required.")
        return 1

    # keyring.set_password() routes to whichever OS-native secret store
    # exists on this machine:
    #   Windows -> Credential Manager (DPAPI-encrypted by the user's profile)
    #   macOS   -> Keychain
    #   Linux   -> Secret Service (GNOME Keyring / KWallet over D-Bus)
    # Same principle as a sealed credential in Datto/Kaseya — the secret
    # never sits on disk in plaintext, and access is gated by the OS user.
    keyring.set_password(SERVICE_NAME, "sender_email", email)
    keyring.set_password(SERVICE_NAME, "sender_password", password)

    print("Credentials have been securely stored in the keyring.")
    return 0


# Python's "main" entry-point guard. `__name__` equals "__main__" only
# when this file is executed directly (e.g. `python setup_credentials.py`).
# If another script does `import setup_credentials`, `__name__` is the
# module name and this block is skipped — so importing the file doesn't
# accidentally re-prompt for credentials.
#
# sys.exit() takes an int and propagates it as the process exit code,
# the same way PowerShell exposes `$LASTEXITCODE`. This lets shell
# pipelines and Task Scheduler detect failure.
if __name__ == "__main__":
    sys.exit(main())
