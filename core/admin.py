# core/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth import get_user_model

from .models import Location

User = get_user_model()


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    # Add your custom fields to admin
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("M2P", {"fields": ("role", "phone")}),
    )
    list_display = ("username", "role", "email", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("username", "email")


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner", "room_count", "is_physio", "is_garage_sale")
    list_filter = ("is_physio", "is_garage_sale")
    search_fields = ("name", "owner__username")
    filter_horizontal = ("consultants",)  # for ManyToMany
