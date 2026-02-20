from __future__ import annotations
from typing import Set
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Prefetch
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from core.models import User
# from .forms import GarageSaleEventForm
from .models import GarageSaleEvent, SaleItem, Reservation, ReservationItem
from django.conf import settings


def home(request):
    return render(request, "garage_sale/home_map.html", {
        "default_map_center": getattr(settings, "DEFAULT_MAP_CENTER", [-37.8136, 144.9631]),
        "default_map_zoom": getattr(settings, "DEFAULT_MAP_ZOOM", 10),
    })


# ----------------------------
# Helpers
# ----------------------------

def _is_owner(user, event: GarageSaleEvent) -> bool:
    return bool(user.is_authenticated and event.owner_id == user.id)


def _current_draft_reservation(user, event: GarageSaleEvent) -> Reservation:
    reservation, _ = Reservation.objects.get_or_create(
        event=event,
        customer=user,
        status=Reservation.Status.DRAFT,
        defaults={"assigned_consultant": event.consultant},
    )
    return reservation


# ----------------------------
# Landing / map
# ----------------------------




def map_data(request):
    """
    Active events ONLY. Coordinates come from event.location (physio Location).
    """
    today = timezone.localdate()
    qs = (
        GarageSaleEvent.objects
        .select_related("location")
        .filter(start_date__lte=today, end_date__gte=today)
        .order_by("-start_date", "-id")
    )

    events = []
    for ev in qs:
        loc = ev.location
        if loc.latitude is None or loc.longitude is None:
            continue

        events.append({
            "id": ev.id,
            "title": ev.title or f"Garage Sale @ {loc.name}",
            "location_name": loc.name,
            "lat": float(loc.latitude),
            "lng": float(loc.longitude),
            "start_date": ev.start_date.isoformat(),
            "end_date": ev.end_date.isoformat(),
            "items_url": reverse("garage_sale:items_list", args=[ev.id]),
            "event_url": reverse("garage_sale:event_detail", args=[ev.id]),
        })

    return JsonResponse({"events": events})


# ----------------------------
# Post-login router
# ----------------------------

@login_required
def post_login_router(request):
    role = getattr(request.user, "role", User.Role.CUSTOMER)

    if role == User.Role.LOCATION_OWNER:
        return redirect("garage_sale:events_list")

    if role == User.Role.CONSULTANT:
        return redirect("garage_sale:consultant_dashboard")

    return redirect("garage_sale:home")


# ----------------------------
# Events
# ----------------------------

def events_list(request):
    today = timezone.localdate()
    events = GarageSaleEvent.objects.select_related("location", "owner", "consultant").order_by("-start_date", "-id")
    return render(request, "garage_sale/events_list.html", {"events": events, "today": today})


def event_detail(request, event_id):
    event = get_object_or_404(GarageSaleEvent.objects.select_related("location", "owner", "consultant"), id=event_id)
    items = event.items.order_by("title", "id")
    return render(request, "garage_sale/event_detail.html", {
        "event": event,
        "items": items,
        "is_owner": _is_owner(request.user, event),
    })


@login_required
def event_create(request):
    if getattr(request.user, "role", None) != User.Role.LOCATION_OWNER:
        return HttpResponseForbidden("Location owners only")

    if request.method == "POST":
        form = GarageSaleEventForm(request.POST, owner=request.user)
        if form.is_valid():
            ev = form.save(commit=False)
            ev.owner = request.user
            ev.save()
            return redirect("garage_sale:events_list")
    else:
        form = GarageSaleEventForm(owner=request.user)

    return render(request, "garage_sale/event_form.html", {"form": form})


# ----------------------------
# Items list + customer selection
# ----------------------------

@login_required
def items_list(request, event_id: int):
    event = get_object_or_404(GarageSaleEvent.objects.select_related("location", "owner", "consultant"), pk=event_id)
    is_owner = _is_owner(request.user, event)

    items = (
        SaleItem.objects
        .filter(event=event, is_listed=True)
        .order_by("title", "id")
    )

    preselected: Set[int] = set()

    if getattr(request.user, "role", None) == User.Role.CUSTOMER:
        reservation = _current_draft_reservation(request.user, event)
        preselected = set(reservation.lines.values_list("item_id", flat=True))

        if request.method == "POST":
            selected_ids = request.POST.getlist("item_ids")
            reservation.lines.all().delete()

            selected_items = items.filter(id__in=selected_ids, quantity_available__gt=0)
            for it in selected_items:
                ReservationItem.objects.create(
                    reservation=reservation,
                    item=it,
                    quantity=1,
                    price_at_time=it.price,
                )

            messages.success(request, "Selection updated.")
            return redirect("garage_sale:cart_review")

    else:
        if request.method == "POST":
            messages.error(request, "Only customers can select items.")
            return redirect("garage_sale:items_list", event_id=event.id)

    return render(request, "garage_sale/items_list.html", {
        "event": event,
        "items": items,
        "preselected": preselected,
        "is_owner": is_owner,
    })


# ----------------------------
# Cart
# ----------------------------

@login_required
def cart_review(request):
    if getattr(request.user, "role", None) != User.Role.CUSTOMER:
        return render(request, "garage_sale/not_allowed.html", status=403)

    reservation = (
        Reservation.objects
        .filter(customer=request.user, status=Reservation.Status.DRAFT)
        .select_related("event", "event__location")
        .prefetch_related("lines__item")
        .order_by("-created_at")
        .first()
    )

    return render(request, "garage_sale/cart_review.html", {"reservation": reservation})


@login_required
def cart_clear(request):
    if getattr(request.user, "role", None) != User.Role.CUSTOMER:
        return redirect("garage_sale:home")

    reservation = (
        Reservation.objects
        .filter(customer=request.user, status=Reservation.Status.DRAFT)
        .order_by("-created_at")
        .first()
    )
    if reservation:
        reservation.lines.all().delete()
        reservation.delete()
        messages.info(request, "Shopping list cleared.")

    return redirect("garage_sale:home")


@login_required
@transaction.atomic
def cart_confirm(request):
    if getattr(request.user, "role", None) != User.Role.CUSTOMER:
        return render(request, "garage_sale/not_allowed.html", status=403)

    reservation = (
        Reservation.objects
        .filter(customer=request.user, status=Reservation.Status.DRAFT)
        .select_related("event", "event__consultant")
        .prefetch_related("lines__item")
        .order_by("-created_at")
        .first()
    )

    if not reservation:
        messages.error(request, "No draft reservation to confirm.")
        return redirect("garage_sale:cart_review")

    lines = list(reservation.lines.select_related("item").all())
    if not lines:
        messages.error(request, "Your shopping list is empty.")
        return redirect("garage_sale:cart_review")

    item_ids = [ln.item_id for ln in lines]
    items_by_id = {it.id: it for it in SaleItem.objects.select_for_update().filter(id__in=item_ids)}

    # validate stock first
    shortages = []
    for ln in lines:
        it = items_by_id.get(ln.item_id)
        if (it is None) or (it.quantity_available < ln.quantity):
            shortages.append((it.title if it else "Unknown", it.quantity_available if it else 0, ln.quantity))

    if shortages:
        for title, available, wanted in shortages:
            messages.error(request, f"Not enough stock for {title}. Available: {available}, in your cart: {wanted}.")
        return redirect("garage_sale:cart_review")

    # decrement stock
    for ln in lines:
        it = items_by_id[ln.item_id]
        it.quantity_available -= ln.quantity
        it.save(update_fields=["quantity_available"])

    if reservation.assigned_consultant_id is None and reservation.event.consultant_id:
        reservation.assigned_consultant = reservation.event.consultant

    reservation.status = Reservation.Status.CONFIRMED
    reservation.confirmed_at = timezone.now()
    reservation.save(update_fields=["assigned_consultant", "status", "confirmed_at"])

    messages.success(request, "Confirmed! Your items are reserved for pickup.")
    return redirect("garage_sale:cart_review")


# ----------------------------
# Item CRUD (owner only)
# ----------------------------

@login_required
def item_create(request, event_id):
    event = get_object_or_404(GarageSaleEvent, id=event_id)
    if not _is_owner(request.user, event):
        return HttpResponseForbidden("Not your event.")

    if request.method == "POST":
        form = SaleItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.event = event
            item.save()
            messages.success(request, "Item added.")
            return redirect("garage_sale:items_list", event_id=event.id)
    else:
        form = SaleItemForm()

    return render(request, "garage_sale/item_form.html", {"form": form, "event": event})


@login_required
def item_edit(request, item_id):
    item = get_object_or_404(SaleItem, id=item_id)
    event = item.event
    if not _is_owner(request.user, event):
        return HttpResponseForbidden("Not your event.")

    if request.method == "POST":
        form = SaleItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, "Item updated.")
            return redirect("garage_sale:items_list", event_id=event.id)
    else:
        form = SaleItemForm(instance=item)

    return render(request, "garage_sale/item_form.html", {"form": form, "event": event, "item": item})


@login_required
def item_delete(request, item_id):
    item = get_object_or_404(SaleItem, id=item_id)
    event = item.event
    if not _is_owner(request.user, event):
        return HttpResponseForbidden("Not your event.")

    if request.method == "POST":
        item.delete()
        messages.success(request, "Item deleted.")
        return redirect("garage_sale:items_list", event_id=event.id)

    return render(request, "garage_sale/item_confirm_delete.html", {"item": item, "event": event})


# ----------------------------
# Consultant dashboard
# ----------------------------

@login_required
def consultant_dashboard(request):
    if getattr(request.user, "role", None) != User.Role.CONSULTANT:
        return render(request, "garage_sale/not_allowed.html", status=403)

    today = timezone.localdate()

    events = (
        GarageSaleEvent.objects
        .select_related("location", "owner", "consultant")
        .filter(end_date__gte=today, consultant=request.user)
        .order_by("start_date", "location__name", "title")
    )

    lines_qs = ReservationItem.objects.select_related("item").order_by("item__title")

    pickups = (
        Reservation.objects
        .select_related("event", "event__location", "customer", "assigned_consultant")
        .prefetch_related(Prefetch("lines", queryset=lines_qs))
        .filter(status=Reservation.Status.CONFIRMED, event__in=events)
        .order_by("event__start_date", "event__location__name", "confirmed_at", "created_at")
    )

    pickups_by_event = {}
    for r in pickups:
        pickups_by_event.setdefault(r.event_id, []).append(r)

    return render(request, "garage_sale/consultant_dashboard.html", {
        "today": today,
        "events": events,
        "pickups_by_event": pickups_by_event,
    })
