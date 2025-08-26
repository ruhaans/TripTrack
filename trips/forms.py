from django import forms
from .models import Registration, Trip
import re
BASE_INPUT = "block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-black/20"

class RegistrationForm(forms.ModelForm):
    class Meta:
        model = Registration
        fields = ["full_name", "phone", "dob", "park_choice"]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": BASE_INPUT, "placeholder": "Your full name"}),
            "phone": forms.TextInput(attrs={"class": BASE_INPUT, "placeholder": "9876543210"}),
            "dob": forms.DateInput(attrs={"type": "date", "class": BASE_INPUT}),
            "park_choice": forms.Select(attrs={"class": BASE_INPUT}),
            
        }

    def clean_phone(self):
        raw = self.cleaned_data.get("phone", "").strip()
        digits = re.sub(r"\D", "", raw)  # strip non-digits

        if len(digits) != 10:
            raise forms.ValidationError("Enter a valid 10-digit Indian phone number.")

        # Normalize to +91 XXXXX XXXXX for storage
        normalized = f"+91 {digits[:5]} {digits[5:]}"
        return normalized

class TripForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = ["name", "date", "meetup_time", "return_time", "pickup_point", "capacity", "is_active"]
        widgets = {
           "name": forms.TextInput(attrs={"class": BASE_INPUT, "placeholder": "e.g., Imagica Day Trip"}),
            "date": forms.DateInput(attrs={"type": "date", "class": BASE_INPUT}),
            "meetup_time": forms.TimeInput(attrs={"type": "time", "class": BASE_INPUT}),
            "return_time": forms.TimeInput(attrs={"type": "time", "class": BASE_INPUT}),
            "pickup_point": forms.TextInput(attrs={"class": BASE_INPUT, "placeholder": "e.g., FC Road (opp. Starbucks)"}),
            "capacity": forms.NumberInput(attrs={"class": BASE_INPUT, "min": 1}),
            "is_active": forms.CheckboxInput(attrs={"class": "h-4 w-4 rounded border-gray-300"}),
            "details": forms.Textarea(attrs={"class": BASE_INPUT, "rows": 6, "placeholder": "Long description, inclusions, pricing, notes…"}),
        }
        

class RegistrationAdminForm(forms.ModelForm):
    class Meta:
        model = Registration
        fields = ["status", "imagica_transaction", "price", "gift_code"]
        widgets = {
            "status": forms.Select(attrs={"class": BASE_INPUT}),
            "imagica_transaction": forms.TextInput(attrs={"class": BASE_INPUT, "placeholder": "Imagica txn / booking ref"}),
            "price": forms.NumberInput(attrs={"class": BASE_INPUT, "min": 0, "step": "1", "placeholder": "1299"}),
            "gift_code": forms.TextInput(attrs={"class": BASE_INPUT, "placeholder": "e.g., EARLYBIRD10"}),
        }