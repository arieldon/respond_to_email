#!/usr/bin/env python3

import argparse
import email
import getpass
import imaplib
import smtplib
import string
import sys
import random
import time


def retry_auth(f):
    def aid(user, attempts = 0):
        if attempts > 2:
            sys.stderr.write("Failure after three tries.\n")
            sys.exit(1)
        try:
            global pswd
            pswd = getpass.getpass()
            f(user, pswd)
        except Exception:
            print("Incorrect, try again.")
            aid(user, attempts + 1)
    return aid


def generate_random_string():
    return "".join(random.sample(string.ascii_letters + string.digits, 8))


def create_message(user, sbj, content):
    msg = email.message.EmailMessage()
    msg.set_content(content)
    msg["subject"] = sbj;
    msg["From"] = user
    msg["To"] = user
    return msg


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
    pswd = ""

    sbj = f"{args.subject} ({generate_random_string()})"
    msg = create_message(user, sbj, args.message)

    with smtplib.SMTP_SSL(host="smtp.gmail.com", port=465) as smtp:
        login = retry_auth(smtp.login)
        login(user)
        smtp.send_message(msg)

    with imaplib.IMAP4_SSL(host="imap.gmail.com") as imap:
        imap.login(user, pswd)
        imap.select("INBOX", readonly=True)

        while True:
            status, data = imap.search(None, f'(SUBJECT "Re: {sbj}")')
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
                imap.noop()
        imap.close()
