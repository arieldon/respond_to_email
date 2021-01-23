#!/usr/bin/env python3

import argparse
import email
import getpass
import imaplib
import smtplib
import string
import random
import time


def generate_random_string():
    return "".join(random.sample(string.ascii_letters + string.digits, 8))


def get_message_contents(message):
    if not message.is_multipart():
        return message.get_payload()
    return "".join(
        [
            part.get_payload()
            for part in message.get_payload()
            if part.get_content_type() == "text/plain"
        ]
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="respond_to_email",
        description="Send an email from a given address to the same address and \
            await a response.",
    )
    parser.add_argument(
        "--subject",
        "-s",
        type=str,
        help="the subject line of the email",
        default="Subject",
    )
    parser.add_argument(
        "--message",
        "-m",
        type=str,
        help="the contents within the email",
        default="This message awaits a reply.",
    )
    args = parser.parse_args()

    user = input("Email: ")
    pswd = getpass.getpass()
    print()

    # Create a message.
    msg = email.message.EmailMessage()
    sbj = f"{args.subject} ({generate_random_string()})"
    msg.set_content(args.message)
    msg["subject"] = sbj
    msg["From"] = user
    msg["To"] = user

    # Send message.
    with smtplib.SMTP_SSL(host="smtp.gmail.com", port=465) as smtp:
        smtp.login(user, pswd)
        smtp.send_message(msg)

    # Parse inbox and return any messages that match the subject line above.
    with imaplib.IMAP4_SSL(host="imap.gmail.com") as imap:
        imap.login(user, pswd)
        imap.select("INBOX", readonly=True)

        while True:
            status, data = imap.search(None, f'(SUBJECT "Re: {sbj}")')


            # `data` will evaluate to `True` whether or not a message is found
            # in the line above because it will bare-minimum contain b'', which
            # means the list contains a value and therefore evaluates to
            # 'True'. But b'' itself is `False`. On the other hand, `data` will
            # contain, say, b'19' or some other significant bytes instead of
            # b'' if a message is found, so the first element will evaluate to
            # `True` in that case.
            if data[0]:
                for datum in data[0].split():
                    status, response_parts = imap.fetch(datum, "(RFC822)")
                    for part in response_parts:
                        if isinstance(part, tuple):
                            message = email.message_from_bytes(part[1])
                            print(f"{message['subject']} [{message['from']}]")
                            print(get_message_contents(message))
                break
            else:
                print("No reply.")
                time.sleep(10)
                """
                The NOOP command always succeeds.  It does nothing.

                Since any command can return a status update as untagged data, the
                NOOP command can be used as a periodic poll for new messages or
                message status updates during a period of inactivity (this is the
                preferred method to do this).  The NOOP command can also be used
                to reset any inactivity autologout timer on the server.

                ---RFC 3501 Internet Message Access Protocol
                """
                imap.noop()

        # Necessary regardless of "with" statement. "with" statement calls
        # `.logout()` automatically, not `.close()`.
        imap.close()
