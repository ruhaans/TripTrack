# accounts/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from .models import User

# Light, reusable Tailwind defaults so even a raw {{ form }} looks OK.
# You can fully redesign in templates when you want (hybrid approach).
BASE_INPUT = (
    "block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm "
    "placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-black/20"
)
BASE_CHECKBOX = "h-4 w-4 rounded border-gray-300 text-black focus:ring-black/30"


class SignupForm(forms.ModelForm):
    """
    Public signup form with basic styling defaults.
    You can handcraft the HTML in templates for full control.
    """

    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"class": BASE_INPUT, "autocomplete": "new-password"}),
        help_text="Use at least 8 characters with a mix of letters and numbers.",
    )
    password2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput(attrs={"class": BASE_INPUT, "autocomplete": "new-password"}),
    )
    accept_terms = forms.BooleanField(
        label="I agree to the terms",
        required=True,
        widget=forms.CheckboxInput(attrs={"class": BASE_CHECKBOX}),
    )

    class Meta:
        model = User
        fields = ["username", "email"]
        widgets = {
            "username": forms.TextInput(
                attrs={"class": BASE_INPUT, "placeholder": "yourname", "autocomplete": "username"}
            ),
            "email": forms.EmailInput(
                attrs={"class": BASE_INPUT, "placeholder": "you@example.com", "autocomplete": "email"}
            ),
        }
        labels = {"username": "Username", "email": "Email address"}

    # ---- validation ----
    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords do not match.")
        if p1 and len(p1) < 8:
            self.add_error("password1", "Password must be at least 8 characters long.")
        return cleaned

    # ---- persistence ----
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].lower().strip()
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    """
    Styled login form (logic uses Django's defaults).
    """

    username = forms.CharField(
        label="Username or email",
        widget=forms.TextInput(
            attrs={"class": BASE_INPUT, "placeholder": "yourname or you@example.com", "autocomplete": "username"}
        ),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"class": BASE_INPUT, "autocomplete": "current-password"}),
    )
