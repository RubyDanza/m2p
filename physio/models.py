import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from core.models import Location  # Location lives in core
# Don't import User from core here; use settings.AUTH_USER_MODEL for relations.


class Appointment(models.Model):
    # Who/what/where
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointments",
    )

    # Keep temporarily so your existing map flow doesn't break
    location_label = models.CharField(max_length=120, blank=True, default="")

    consultant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consultant_appointments",
        limit_choices_to={"role": "CONSULTANT"},  # avoids importing User
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_appointments",
    )

    # Customer identity (until you add customer FK later)
    customer_label = models.CharField(max_length=80, blank=True, default="Guest")

    # When
    date = models.DateField()
    time = models.TimeField()

    # Room allocation
    room_number = models.PositiveSmallIntegerField(null=True, blank=True)

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        DECLINED = "DECLINED", "Declined"

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )

    # Consultant action links
    action_token = models.UUIDField(default=uuid.uuid4, editable=False)
    action_token_expires_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["consultant", "date", "time"],
                condition=Q(status="ACCEPTED") & Q(consultant__isnull=False),
                name="uniq_consultant_timeslot_when_accepted",
            ),
            models.UniqueConstraint(
                fields=["location", "date", "time", "room_number"],
                condition=Q(status="ACCEPTED") & Q(location__isnull=False) & Q(room_number__isnull=False),
                name="uniq_room_timeslot_when_accepted",
            ),
        ]

    def refresh_action_token(self, hours=48):
        self.action_token = uuid.uuid4()
        self.action_token_expires_at = timezone.now() + timedelta(hours=hours)


def pick_available_room(*, location, date, time):
    """
    Return lowest free room number (1..room_count) for ACCEPTED appts at this slot.
    """
    if not location or not location.room_count:
        return None

    taken = set(
        Appointment.objects.filter(
            location=location,
            date=date,
            time=time,
            status="ACCEPTED",
            room_number__isnull=False,
        ).values_list("room_number", flat=True)
    )

    for rn in range(1, int(location.room_count) + 1):
        if rn not in taken:
            return rn
    return None
