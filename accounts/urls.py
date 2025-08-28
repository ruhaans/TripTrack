# accounts/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views

from .forms import LoginForm
from .views import signup, verify_email, resend_verification, after_login

app_name = "accounts"

urlpatterns = [
    # Signup & verification
    path("signup/", signup, name="signup"),
    path("verify/<str:token>/", verify_email, name="verify-email"),
    path("resend-verification/", resend_verification, name="resend-verification"),
    path("after-login/", after_login, name="after-login"),

    # Login/Logout (Django built-ins with custom form)
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html",
            authentication_form=LoginForm,
        ),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(next_page="accounts:login"),
        name="logout",
    ),
]
