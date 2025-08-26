# accounts/views.py
from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.mail import send_mail
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .forms import SignupForm

User = get_user_model()
SIGN_SALT = "triptrack.email.verify"   # single salt used everywhere


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _verification_link(request, user: User) -> str:
    token = signing.dumps({"uid": user.pk, "email": user.email}, salt=SIGN_SALT)
    return request.build_absolute_uri(reverse("accounts:verify-email", kwargs={"token": token}))

def _send_verification_email(request, user: User) -> None:
    url = _verification_link(request, user)
    subject = "Verify your email for TripTrack"
    body = (
        f"Hi {user.username},\n\n"
        f"Please verify your email by clicking this link:\n{url}\n\n"
        f"If you didn't sign up, you can ignore this message."
    )
    send_mail(
        subject,
        body,
        getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@triptrack.local"),
        [user.email],
        fail_silently=False,
    )


# ---------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------

@require_http_methods(["GET", "POST"])
def signup(request):
    """
    Create account -> send verification email -> auto-login -> redirect:
      staff -> /manage/, users -> /trip/
    'Join this trip' is still blocked until email_verified=True.
    """
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Send verification mail
            _send_verification_email(request, user)

            # Auto-login new user
            login(request, user)

            messages.success(
                request,
                "Account created. We’ve sent a verification email — please verify to join the trip."
            )
            return redirect("accounts:after-login")  # staff->manage, user->
    else:
        form = SignupForm()
    return render(request, "accounts/signup.html", {"form": form})


def verify_email(request, token: str):
    """
    Verify email from the signed token. Link is valid for 3 days.
    If user is logged in, go to My Trip; else send them to Login.
    """
    try:
        data = signing.loads(token, salt=SIGN_SALT, max_age=60 * 60 * 24 * 3)
        uid = data.get("uid")
        email = data.get("email")
    except signing.BadSignature:
        return HttpResponseBadRequest("Invalid or expired verification link.")

    try:
        user = User.objects.get(pk=uid, email=email)
    except User.DoesNotExist:
        return HttpResponseBadRequest("User not found for this token.")

    if not getattr(user, "email_verified", False):
        user.email_verified = True
        user.save(update_fields=["email_verified"])
        messages.success(request, "Email verified successfully! You can now join the trip.")
    else:
        messages.info(request, "Your email is already verified.")

    # If they’re logged in on this browser, take them to their hub; otherwise to login.
    return redirect("trips:home" if request.user.is_authenticated else "login")


@login_required
def resend_verification(request):
    """Logged-in users can resend the verification email."""
    if getattr(request.user, "email_verified", False):
        messages.info(request, "Your email is already verified.")
        return redirect("trips:home")
    _send_verification_email(request, request.user)
    messages.success(request, "Verification email sent again. Check your inbox.")
    return redirect("trips:home")


# Optional: role-aware post-login redirect used by LOGIN_REDIRECT_URL
@login_required
def after_login(request):
    """
    Send staff to Organizer dashboard, everyone else to My Trip.
    Hook this with: LOGIN_REDIRECT_URL = 'accounts:after-login'
    """
    if request.user.is_staff:
        return redirect("trips:manage")
    return redirect("trips:home")
