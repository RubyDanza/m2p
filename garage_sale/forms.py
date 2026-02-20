from __future__ import annotations

from django import forms
from django.utils import timezone
from core.models import Location
from .models import GarageSaleEvent, SaleItem


class GarageSaleEventForm(forms.ModelForm):
    """
    Owner creates an event at one of their Locations.
    Pass owner=request.user so the Location dropdown is filtered.
    """

    class Meta:
        model = GarageSaleEvent
        fields = ["location", "title", "start_date", "end_date", "notes"]
        widgets = {
            "location": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "end_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop("owner", None)
        super().__init__(*args, **kwargs)

        if owner is not None:
            self.fields["location"].queryset = Location.objects.filter(owner=owner).order_by("name")
        else:
            self.fields["location"].queryset = Location.objects.none()

        if not self.instance.pk and not self.is_bound:
            today = timezone.localdate()
            self.initial.setdefault("start_date", today)
            self.initial.setdefault("end_date", today)

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        if start and end and end < start:
            raise forms.ValidationError("End date cannot be earlier than start date.")
        return cleaned


class SaleItemForm(forms.ModelForm):
    class Meta:
        model = SaleItem
        fields = ["title", "description", "price", "quantity_available", "is_listed"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "price": forms.NumberInput(attrs={"class": "form-control"}),
            "quantity_available": forms.NumberInput(attrs={"class": "form-control"}),
            "is_listed": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
