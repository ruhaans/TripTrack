# accounts/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

BASE_INPUT = "block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-black/20"
BASE_LABEL = "block text-sm font-medium text-gray-700 mb-1"
BASE_HELP  = "text-xs text-gray-500 mt-1"
BASE_ERR   = "text-xs text-red-600 mt-1"

class SignupForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["username", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Tailwind classes to widgets
        for name, field in self.fields.items():
            css = BASE_INPUT
            if isinstance(field.widget, forms.CheckboxInput):
                css = ""  # not used here, but pattern for future
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} {css}".strip()

            # placeholders (optional)
            if name == "username":
                field.widget.attrs["placeholder"] = "Choose a username"
            if name == "email":
                field.widget.attrs["placeholder"] = "you@example.com"
        # Passwords too
        self.fields["password1"].widget.attrs.update({
            "class": BASE_INPUT, "placeholder": "Create a password"
        })
        self.fields["password2"].widget.attrs.update({
            "class": BASE_INPUT, "placeholder": "Re-enter password"
        })

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email is already registered.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords do not match.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].lower().strip()
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user
