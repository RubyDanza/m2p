# garage_sale/admin.py
from django.contrib import admin
from .models import GarageSaleEvent, SaleItem, Reservation, ReservationItem


@admin.register(GarageSaleEvent)
class GarageSaleEventAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "start_date", "end_date", "owner")  # removed created_at
    list_filter = ("start_date", "end_date")
    search_fields = ("title", "owner__username")
    ordering = ("-start_date", "-id")



@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "event", "price", "quantity_available", "is_listed", "created_at")
    list_filter = ("is_listed",)
    search_fields = ("title", "event__title")
    ordering = ("title", "id")


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("id", "event", "customer", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("customer__username", "event__title")
    ordering = ("-created_at",)


@admin.register(ReservationItem)
class ReservationItemAdmin(admin.ModelAdmin):
    list_display = ("id", "reservation", "item", "quantity", "price_at_time")
    ordering = ("-id",)
