from django.urls import path
from .views import signup, verify_email, resend_verification, after_login

app_name = "accounts"
urlpatterns = [
    path("signup/", signup, name="signup"),
    path("verify/<str:token>/", verify_email, name="verify-email"),
    path("resend/", resend_verification, name="resend-verification"),
    path("after-login/", after_login, name="after-login"),  # role-aware redirect
]
