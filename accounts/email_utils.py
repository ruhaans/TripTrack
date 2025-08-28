# accounts/email_utils.py
from django.core import signing
from django.urls import reverse
from django.template.loader import render_to_string
from django.conf import settings

from triptrack.utils import absolute_url
from triptrack.mailer import send_email

SIGN_SALT = "triptrack.email.verify"  # keep this stable

def make_verification_link(user) -> str:
    token = signing.dumps({"uid": user.pk, "email": user.email}, salt=SIGN_SALT)
    path = reverse("accounts:verify-email", kwargs={"token": token})
    return absolute_url(path)

def send_verification_email(user) -> None:
    url = make_verification_link(user)
    subject = "Verify your email for TripTrack"

    ctx = {
        "username": user.username or (user.email.split("@")[0] if user.email else "there"),
        "verify_url": url,
    }

    text_body = render_to_string("emails/verify_email.txt", ctx)
    html_body = render_to_string("emails/verify_email.html", ctx)
    # If you want replies to go somewhere human:
    # reply_to = "info@triptrack.online"
    send_email(subject, [user.email], text_body, html_body, reply_to=None)
