from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction

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


class RegisterForm(UserCreationForm):
    role = forms.ChoiceField(choices=User.ROLE_CHOICES, label="I am a")
    org_name = forms.CharField(max_length=120, label="Restaurant / hall / organisation name")
    phone = forms.CharField(max_length=20, required=False, label="Phone")

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
        return self.cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.cleaned_data["role"]
        user.save()
        model = Restaurant if user.role == User.RESTAURANT else ConventionHall
        model.objects.create(
            owner=user,
            name=self.cleaned_data["org_name"],
            phone=self.cleaned_data.get("phone", ""),
            address=self.cleaned_data.get("address", ""),
            **{lvl: self.cleaned_data[lvl] for lvl in LEVELS},
        )
        return user


class FoodItemForm(forms.ModelForm):
    class Meta:
        model = FoodItem
        fields = ["name", "description", "quality", "price", "quantity", "image", "is_active"]
        widgets = {"price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
                   "quantity": forms.NumberInput(attrs={"min": "0"})}
