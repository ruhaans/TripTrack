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
from trips.utils.urls import absolute_url
from accounts.email_utils import send_verification_email
from .forms import SignupForm
from accounts.email_utils import SIGN_SALT
User = get_user_model()
# SIGN_SALT = "triptrack.email.verify"   # single salt used everywhere


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

# def _verification_link(request, user: User) -> str:
#     token = signing.dumps({"uid": user.pk, "email": user.email}, salt=SIGN_SALT)
#     return request.build_absolute_uri(reverse("accounts:verify-email", kwargs={"token": token}))

def _verification_link(user):
    token = signing.dumps({"uid": user.pk, "email": user.email}, salt=SIGN_SALT)
    path = reverse("accounts:verify-email", kwargs={"token": token})
    return absolute_url(path)

def _send_verification_email(request, user):
    send_verification_email(user)


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
            return redirect("accounts:after-login")  # staff->manage, user->home
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
        # Friendlier UX than a raw 400: show a small template later if you like
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
    return redirect("trips:home" if request.user.is_authenticated else "accounts:login")


# -------------------- Resend Verification (UX page) --------------------

@login_required
@require_http_methods(["GET", "POST"])
def resend_verification(request):
    """
    UX page for resending the verification email.

    - GET  -> render a page with a button (disabled if already verified)
    - POST -> send the email (unless already verified), then redisplay page with a message
    """
    user = request.user

    if request.method == "POST":
        if getattr(user, "email_verified", False):
            messages.info(request, "Your email is already verified.")
            return redirect("accounts:resend-verification")

        _send_verification_email(request, user)
        messages.success(request, f"Verification email sent to {user.email}. Check your inbox.")
        return redirect("accounts:resend-verification")

    # GET: render the page
    context = {
        "email": user.email,
        "is_verified": bool(getattr(user, "email_verified", False)),
    }
    return render(request, "accounts/resend_verification.html", context)


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
