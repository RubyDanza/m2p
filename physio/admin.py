# physio/admin.py
from django.contrib import admin
from .models import Appointment

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("id", "date", "time", "location", "consultant", "created_by", "status", "room_number")
    list_filter = ("status", "date", "location")
    search_fields = ("location__name", "consultant__username", "created_by__username")
    ordering = ("-date", "-time", "-id")

