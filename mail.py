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


def retry_auth(attempts=3):
    """
    Grant the user a certain number of attempts to authenticate before exiting
    with a status of 1. Upon success, return the password and proceed.
    """
    def decorate_retry(f):
        def retry_function(user):
            pswd = ""
            remaining_attempts = attempts
            while remaining_attempts > 0:
                pswd = getpass.getpass()
                try:
                    f(user, pswd)
                except Exception as e:
                    remaining_attempts -= 1
                    if remaining_attempts == 0:
                        print(f"Failure after {attempts} attempts.")
                        sys.exit(1)
                    else:
                        print("Incorrect password, try again.")
                else:
                    return pswd
        return retry_function
    return decorate_retry


def generate_random_string():
    return "".join(random.sample(string.ascii_letters + string.digits, 8))


def create_message(user, sbj, content):
    msg = email.message.EmailMessage()
    msg.set_content(content)
    msg["subject"] = sbj
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


def parse_reply(imap_instance, reply):
    for datum in reply.split():
        _, response_parts = imap_instance.fetch(datum, "(RFC822)")
        for part in response_parts:
            if isinstance(part, tuple):
                return get_message_contents(email.message_from_bytes(part[1]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="await_email_reply",
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
    parser.add_argument(
        "--delay",
        "-d",
        type=int,
        help="delay between inbox queries when searching for message",
        default=10,
    )
    args = parser.parse_args()

    user = input("Email: ")
    pswd = ""

    sbj = f"{args.subject} ({generate_random_string()})"
    msg = create_message(user, sbj, args.message)

    with smtplib.SMTP_SSL(host="smtp.gmail.com", port=465) as smtp:
        pswd = retry_auth()(smtp.login)(user)
        smtp.send_message(msg)

    with imaplib.IMAP4_SSL(host="imap.gmail.com") as imap:
        imap.login(user, pswd)
        imap.select("INBOX", readonly=True)

        while True:
            _, search_result = imap.search(None, f'(SUBJECT "Re: {sbj}")')
            if search_result[0]:
                print(parse_reply(imap, reply=search_result[0]))
                break
            else:
                print("No reply.")
                time.sleep(args.delay)
                imap.noop()
        imap.close()
