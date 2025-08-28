# triptrack/mailer.py
from typing import Iterable, Optional
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

def send_email(
    subject: str,
    to: Iterable[str],
    text_body: str,
    html_body: Optional[str] = None,
    reply_to: Optional[str] = None,
) -> None:
    headers = {"Reply-To": reply_to} if reply_to else None
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,  # TripTrack <noreply@triptrack.online>
        to=list(to),
        headers=headers,
    )
    if html_body:
        msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)
