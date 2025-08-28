# accounts/views.py
from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django import forms
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
    try:
        data = signing.loads(token, salt=SIGN_SALT, max_age=60*60*24*3)
        uid = data.get("uid")
        email_in_token = (data.get("email") or "").strip().lower()
    except signing.BadSignature:
        return HttpResponseBadRequest("Invalid or expired verification link.")

    try:
        user = User.objects.get(pk=uid)
    except User.DoesNotExist:
        return HttpResponseBadRequest("User not found.")

    if user.email.strip().lower() == email_in_token:
        if not user.email_verified:
            user.email_verified = True
            user.save(update_fields=["email_verified"])
            messages.success(request, "Email verified successfully!")
        else:
            messages.info(request, "Your email is already verified.")
        return redirect("trips:home" if request.user.is_authenticated else "accounts:login")

    return HttpResponseBadRequest("Verification link does not match.")



# -------------------- Resend Verification (UX page) --------------------

class InlineEmailChangeForm(forms.Form):
    new_email = forms.EmailField(label="New email")


@login_required
@require_http_methods(["GET", "POST"])
def resend_verification(request):
    """
    One page that supports:
    - Resending verification to the current email
    - Updating the (unverified) email and sending a new link
    """
    user = request.user
    is_verified = bool(getattr(user, "email_verified", False))

    # Pre-fill the inline form with the current email
    email_form = InlineEmailChangeForm(
        initial={"new_email": user.email},
        data=request.POST or None,
    )

    if request.method == "POST":
        action = request.POST.get("action", "resend")

        # If already verified, nothing to do here.
        if is_verified:
            messages.info(request, "Your email is already verified.")
            return redirect("accounts:resend-verification")

        if action == "update_email":
            # Validate and update the email, then send a new link
            if email_form.is_valid():
                new_email = email_form.cleaned_data["new_email"].strip().lower()

                # Enforce uniqueness
                if User.objects.filter(email__iexact=new_email).exclude(pk=user.pk).exists():
                    email_form.add_error("new_email", "This email is already in use.")
                else:
                    user.email = new_email
                    user.email_verified = False
                    user.save(update_fields=["email", "email_verified"])

                    send_verification_email(user)
                    messages.success(request, f"Email updated. Verification sent to {new_email}.")
                    return redirect("accounts:resend-verification")

        else:  # action == "resend" (default)
            send_verification_email(user)
            messages.success(request, f"Verification email sent to {user.email}.")
            return redirect("accounts:resend-verification")

    # GET or invalid POST -> render page
    context = {
        "email": user.email,
        "is_verified": is_verified,
        "email_form": email_form,
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
