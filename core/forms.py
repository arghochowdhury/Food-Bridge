import re
from datetime import timedelta

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import (ConventionHall, District, Division, FoodItem, PostOffice,
                     Restaurant, Thana, Upazila, User)

LEVELS = ["division", "district", "upazila", "thana", "post_office"]
PARENT = {"district": "division", "upazila": "district", "thana": "upazila", "post_office": "thana"}


def add_location_fields(form):
    form.fields["division"] = forms.ModelChoiceField(Division.objects.all())
    form.fields["district"] = forms.ModelChoiceField(District.objects.all())
    form.fields["upazila"] = forms.ModelChoiceField(Upazila.objects.all())
    form.fields["thana"] = forms.ModelChoiceField(Thana.objects.all())
    form.fields["post_office"] = forms.ModelChoiceField(PostOffice.objects.all())
    form.fields["address"] = forms.CharField(max_length=255, required=False, label="Street address / landmark")


def validate_location(form):
    data = form.cleaned_data
    for child, parent in PARENT.items():
        child_obj, parent_obj = data.get(child), data.get(parent)
        if child_obj and parent_obj and getattr(child_obj, parent) != parent_obj:
            form.add_error(child, f"This {child.replace('_', ' ')} does not belong to the selected {parent}.")


LICENSE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9/\-.\s]{3,38}[A-Za-z0-9]$")


def validate_license(value, exclude_pk=None):
    value = re.sub(r"\s+", " ", (value or "").strip()).upper()
    if not LICENSE_RE.match(value):
        raise ValidationError("Enter a valid trade license number (letters, digits, / - . only, 5 to 40 characters).")
    qs = Restaurant.objects.filter(trade_license_no__iexact=value)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    if qs.exists():
        raise ValidationError("This trade license number is already registered on Food Bridge.")
    return value


class RegisterForm(UserCreationForm):
    role = forms.ChoiceField(choices=User.ROLE_CHOICES, label="I am a")
    org_name = forms.CharField(max_length=120, label="Restaurant / hall / organisation name")
    phone = forms.CharField(max_length=20, required=False, label="Phone")
    trade_license_no = forms.CharField(max_length=40, required=False, label="Trade license number")

    class Meta:
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        add_location_fields(self)

    def clean(self):
        super().clean()
        validate_location(self)
        role = self.cleaned_data.get("role")
        lic = (self.cleaned_data.get("trade_license_no") or "").strip()
        if role == User.RESTAURANT:
            if not lic:
                self.add_error("trade_license_no", "Restaurants must enter a trade license number.")
            else:
                try:
                    self.cleaned_data["trade_license_no"] = validate_license(lic)
                except ValidationError as e:
                    self.add_error("trade_license_no", e)
        else:
            self.cleaned_data["trade_license_no"] = ""
        return self.cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.cleaned_data["role"]
        user.save()
        model = Restaurant if user.role == User.RESTAURANT else ConventionHall
        extra = {"trade_license_no": self.cleaned_data["trade_license_no"]} if user.role == User.RESTAURANT else {}
        model.objects.create(
            owner=user,
            **extra,
            name=self.cleaned_data["org_name"],
            phone=self.cleaned_data.get("phone", ""),
            address=self.cleaned_data.get("address", ""),
            **{lvl: self.cleaned_data[lvl] for lvl in LEVELS},
        )
        return user


class LicenseForm(forms.Form):
    trade_license_no = forms.CharField(max_length=40, label="Trade license number")

    def __init__(self, *args, restaurant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.restaurant = restaurant

    def clean_trade_license_no(self):
        return validate_license(self.cleaned_data["trade_license_no"],
                                exclude_pk=self.restaurant.pk if self.restaurant else None)


class FoodItemForm(forms.ModelForm):
    duration_hours = forms.IntegerField(
        min_value=1, max_value=720, required=False, label="Or available for the next (hours)",
        widget=forms.NumberInput(attrs={"min": "1", "max": "720", "placeholder": "e.g. 3"}))

    class Meta:
        model = FoodItem
        fields = ["name", "description", "quality", "price", "quantity", "image", "is_active", "available_until"]
        widgets = {
            "price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "quantity": forms.NumberInput(attrs={"min": "0"}),
            "available_until": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }
        labels = {"available_until": "Available until (date and time)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["available_until"].input_formats = [
            "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"]

    def clean(self):
        cleaned = super().clean()
        until, hours = cleaned.get("available_until"), cleaned.get("duration_hours")
        if until and hours:
            self.add_error("duration_hours", "Use either an end date and time, or a number of hours, not both.")
        elif hours:
            cleaned["available_until"] = timezone.now() + timedelta(hours=hours)
        elif until and until <= timezone.now():
            self.add_error("available_until", "Choose a time in the future, or clear this field for no time limit.")
        return cleaned
