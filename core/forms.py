from django import forms
from .models import Location

class LocationForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = ["name", "room_count", "latitude", "longitude", "is_physio", "is_garage_sale"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "room_count": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 3}),
            "latitude": forms.NumberInput(attrs={"class": "form-control", "step": "any"}),
            "longitude": forms.NumberInput(attrs={"class": "form-control", "step": "any"}),
        }
