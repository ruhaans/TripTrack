# trips/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Registration, Trip

# Light Tailwind defaults so raw {{ form }} renders decently.
# You can fully handcraft pages in templates (hybrid approach).
BASE_INPUT = (
    "block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm "
    "placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-black/20"
)
BASE_CHECK = "h-4 w-4 rounded border-gray-300 text-black focus:ring-black/30"
BASE_TEXTAREA = (
    "block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm min-h-[120px] "
    "placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-black/20"
)


# ---------------------------- Registration ----------------------------

class RegistrationForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=60,
        required=True,
        widget=forms.TextInput(attrs={"class": BASE_INPUT, "placeholder": "Rahul"}),
        label="First name",
    )
    last_name = forms.CharField(
        max_length=60,
        required=True,  # make it required now
        widget=forms.TextInput(attrs={"class": BASE_INPUT, "placeholder": "Sharma"}),
        label="Last name",
    )

    class Meta:
        model = Registration
        fields = ["first_name", "last_name", "phone", "dob", "park_choice"]
        widgets = {
            "phone": forms.TextInput(attrs={
                "class": BASE_INPUT + " phone-input",
                "placeholder": "98765 43210",
                "inputmode": "numeric",
                "autocomplete": "tel",
            }),
            "dob": forms.DateInput(attrs={"type": "date", "class": BASE_INPUT}),
            "park_choice": forms.Select(attrs={"class": BASE_INPUT}),
        }

    def clean_phone(self):
        raw = (self.cleaned_data.get("phone") or "").strip()
        digits = "".join(ch for ch in raw if ch.isdigit())
        if len(digits) < 10:
            raise ValidationError("Enter a valid phone number (10 digits).")
        return digits

    def clean_dob(self):
        dob = self.cleaned_data.get("dob")
        if not dob:
            raise ValidationError("Date of birth is required.")
        if dob >= timezone.localdate():
            raise ValidationError("DOB cannot be today or in the future.")
        return dob

    def save(self, commit=True):
        reg = super().save(commit=False)
        # Join first+last into the old full_name field
        reg.full_name = f"{self.cleaned_data['first_name']} {self.cleaned_data['last_name']}".strip()
        if commit:
            reg.save()
        return reg

# ------------------------------- Trip ---------------------------------

class TripForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = [
            "name",
            "date",
            "meetup_time",
            "return_time",
            "pickup_point",
            "capacity",
            "is_active",
            "details",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": BASE_INPUT, "placeholder": "Trip name"}),
            "date": forms.DateInput(attrs={"type": "date", "class": BASE_INPUT}),
            "meetup_time": forms.TimeInput(attrs={"type": "time", "class": BASE_INPUT}),
            "return_time": forms.TimeInput(attrs={"type": "time", "class": BASE_INPUT}),
            "pickup_point": forms.TextInput(attrs={"class": BASE_INPUT, "placeholder": "Pickup point/address"}),
            "capacity": forms.NumberInput(attrs={"class": BASE_INPUT, "min": 0, "step": "1"}),
            "is_active": forms.CheckboxInput(attrs={"class": BASE_CHECK}),
            "details": forms.Textarea(attrs={"class": BASE_TEXTAREA, "placeholder": "Inclusions, notes, pricing…"}),
        }

    # ---- validation ----
    def clean_capacity(self):
        cap = self.cleaned_data.get("capacity")
        if cap is None or cap < 0:
            raise ValidationError("Capacity must be zero or greater.")
        return cap


# ------------------------- Registration (Admin) ------------------------

class RegistrationAdminForm(forms.ModelForm):
    class Meta:
        model = Registration
        fields = ["status", "imagica_transaction", "price", "gift_code", "boarded_outbound", "boarded_return"]
        widgets = {
            "status": forms.Select(attrs={"class": BASE_INPUT}),
            "imagica_transaction": forms.TextInput(
                attrs={"class": BASE_INPUT, "placeholder": "Imagica txn / booking ref"}
            ),
            "price": forms.NumberInput(attrs={"class": BASE_INPUT, "min": 0, "step": "1", "placeholder": "1299"}),
            "gift_code": forms.TextInput(attrs={"class": BASE_INPUT, "placeholder": "e.g., EARLYBIRD10"}),
            "boarded_outbound": forms.CheckboxInput(attrs={"class": BASE_CHECK}),
            "boarded_return": forms.CheckboxInput(attrs={"class": BASE_CHECK}),
        }
        labels = {
            "imagica_transaction": "Imagica transaction",
            "price": "Price (₹)",
        }
