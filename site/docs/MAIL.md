# Mogwai Mail: local IMAP input adapter

scripts/m.mail.py is a Python 3 standard-library IMAP watcher for personal
mailboxes. Run it on the **device whose clipboard you want to change**, for
example Android Termux. A script on a VPS cannot change a phone's clipboard
without a separately authenticated transport.

This adapter requires an existing IMAP account. It is **not** an SMTP server,
does not create mailboxes, and does not bypass two-factor authentication.
It copies a matched code for its owner to paste manually. No codes are sent
to ChatGPT or any external endpoint.

## Configuration

1. Clone/download Mogwai. Copy config/mail.example.json to a local path such
   as ~/.config/mogwai/mail.json. Or use the static mail.html config generator.
2. Use the exact IMAP hostname, username, and port from your working mail
   client. If Thunderbird receives john@rigler.org, its incoming server
   settings are the authoritative starting point, not the domain's MX record.
3. Set at least one exact, verified sender address in each rule's "from" array.
   Optionally constrain the subject with "subjectContains". The "codeRegex"
   must be a Python regular expression with one capturing group returning a
   six-digit number. Ambiguous messages with different matches are skipped.
   Multiple aliases arriving in one INBOX can share a login and have different
   rules; distinct IMAP logins need separate account entries.
4. Keep passwords out of Git, JSON configuration and browser forms. The
   "passwordEnv" field identifies the environment variable to use for login.

Termux setup (Termux:API companion app must match Termux signing source):

~~~sh
pkg install python tmux termux-api
mkdir -p "$HOME/.config/mogwai"
cp config/mail.example.json "$HOME/.config/mogwai/mail.json"
# Edit file with Thunderbird IMAP settings and the genuine sender address.
python scripts/m.mail.py --config "$HOME/.config/mogwai/mail.json" --check
tmux new -s mogwai-mail
# In the tmux shell:
read -r -s -p 'IMAP password: ' MOGWAI_MAIL_PASSWORD; printf '\n'
export MOGWAI_MAIL_PASSWORD
python scripts/m.mail.py --config "$HOME/.config/mogwai/mail.json" --notify
~~~

Detach from tmux with Ctrl+B, then D. A new shell/session restart requires
entering the secret again. Android background restrictions can stop Termux;
consider allowing unrestricted background battery and using termux-wake-lock.

One-off diagnostic: python scripts/m.mail.py --config PATH --once --dry-run
(dry-run does not advance an existing UID checkpoint or touch the clipboard).
--check only validates configuration. The first successful run creates an IMAP
UID baseline and *skips old messages*. Request a fresh code afterward.

Checkpoint state is written to ~/.local/state/mogwai/mail/<account-id>.json
and consists only of last UID and UIDVALIDITY; no email bodies, codes or
passwords are saved. The mail From header is not proof of authenticity:
sender headers can be spoofed. Always confirm which site you're pasting into.
Clipboard data can be accessed by authorized apps on the device. Keep private
config, secrets and runtime state out of public repositories.

## Architecture and future adapters

The first output is Termux clipboard via termux-clipboard-set. Optional
termux-notification tells the owner that the clipboard is ready without
showing the code. This IMAP adapter is separate from scripts/m.watch.py,
which polls public URLs. A later FileProxy/Daisy adapter should ingest only
selected non-secret messages with explicit retention configuration, never
archive unsolicited mail or verification codes by default.

The generator at mail.html works when hosted statically or on IPFS, and only
downloads a local JSON config. It cannot run IMAP from a website.

## Outbound delivery is a separate problem

If email sent as @rigler.org looks suspicious, investigate SPF, DKIM, DMARC
alignment, authenticated SMTP submission, reverse DNS/PTR (for self-hosting),
and sending IP/domain reputation. That does not block this incoming mail
watcher, and the watcher does not attempt to reconfigure DNS or SMTP.

## Tests

~~~sh
python3 -m unittest discover -s tests -p 'test_m_mail.py' -v
~~~
