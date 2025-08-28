# accounts/email_utils.py
from django.core import signing
from django.urls import reverse
from django.template.loader import render_to_string
from django.conf import settings

from triptrack.utils import absolute_url
from triptrack.mailer import send_email

SIGN_SALT = "triptrack.email.verify"  # keep consistent everywhere

def make_verification_link(user) -> str:
    token = signing.dumps({"uid": user.pk, "email": user.email}, salt=SIGN_SALT)
    path = reverse("accounts:verify-email", kwargs={"token": token})
    return absolute_url(path)

def send_verification_email(user) -> None:
    if not user.email:
        return
    verify_url = make_verification_link(user)
    ctx = {"username": user.username or user.email.split("@")[0], "verify_url": verify_url}
    subject = "Verify your email for TripTrack"
    text_body = render_to_string("emails/verify_email.txt", ctx)
    html_body = render_to_string("emails/verify_email.html", ctx)
    send_email(subject=subject, to=[user.email], text_body=text_body, html_body=html_body)

