from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer"
        CONSULTANT = "CONSULTANT", "Consultant"
        LOCATION_OWNER = "LOCATION_OWNER", "Location Owner"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, default="")


class Location(models.Model):
    name = models.CharField(max_length=120)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_locations",
        limit_choices_to={"role": "LOCATION_OWNER"},
    )

    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    consultants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="consultant_locations",
        limit_choices_to={"role": "CONSULTANT"},
    )

    room_count = models.PositiveSmallIntegerField(default=1)

    # (Optional) service flags
    is_physio = models.BooleanField(default=True)
    is_garage_sale = models.BooleanField(default=False)

    def __str__(self):
        return self.name
