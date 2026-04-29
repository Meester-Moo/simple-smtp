# simple-smtp

A small command-line tool that sends email over SMTP, using the operating
system's keyring (Windows Credential Manager / macOS Keychain / Linux Secret
Service) to keep credentials out of source code, environment files, and shell
history.

## Requirements

- Python 3.10+
- A SMTP account that allows programmatic login. For Gmail, that means
  enabling 2-Step Verification and generating an **App Password**:
  <https://support.google.com/accounts/answer/185833>

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

Store your sender credentials in the OS keyring (run once):

```bash
python setup_credentials.py
```

You can verify they were stored correctly with:

```bash
python check_credentials.py
```

The password is never printed — the check only confirms it is present.

## Sending mail

```bash
python sendmail.py --to recipient@example.com \
                   --subject "Hello" \
                   --body "This is a test."
```

Short flags work too:

```bash
python sendmail.py -t recipient@example.com -s "Hello" -b "This is a test."
```

### Using a non-Gmail SMTP server

`--smtp-host` and `--smtp-port` default to `smtp.gmail.com:465`. Override them
to use any SMTP server:

```bash
# Office 365 example (STARTTLS on port 587)
python sendmail.py -t user@example.com -s Hi -b Hello \
                   --smtp-host smtp.office365.com --smtp-port 587
```

The script picks the right TLS mode based on the port:

- **Port 465** — implicit TLS (the TLS handshake happens before any SMTP
  commands are exchanged). Historically called SMTPS.
- **Any other port (typically 587)** — STARTTLS. The connection opens in
  plaintext, then the client issues `STARTTLS` and the connection is upgraded
  to TLS before the password is sent.

Both modes encrypt the password before it leaves your machine. Plain port 25
is **not** supported on purpose — it is the legacy server-to-server port and
does not require encryption.

## Files

| File                   | Purpose                                                                                                  |
| ---------------------- | -------------------------------------------------------------------------------------------------------- |
| `setup_credentials.py` | One-time prompt that stores the sender email + password in the OS keyring under service name `smtp_cli`. |
| `check_credentials.py` | Verifies that credentials are retrievable. Never prints the password.                                    |
| `sendmail.py`          | The actual CLI: validates args, pulls credentials from the keyring, sends the message.                   |

## How credentials are stored

`keyring.set_password("smtp_cli", "sender_email", ...)` writes to the OS
secret store rather than a file in the repo or an environment variable. To
remove credentials, use the OS tool (Windows: _Credential Manager → Windows
Credentials_) or:

```python
import keyring
keyring.delete_password("smtp_cli", "sender_email")
keyring.delete_password("smtp_cli", "sender_password")
```

## Exit codes

All three scripts exit `0` on success and `1` on any handled error
(missing credentials, auth failure, DNS failure, recipient rejected, etc.).
This makes the tool composable with shell pipelines and scheduled tasks.
