from django.urls import path
from . import views

app_name = "garage_sale"

urlpatterns = [
    path("", views.home, name="home"),
    path("map-data/", views.map_data, name="map_data"),
    path("events/", views.events_list, name="events_list"),
    # path("events/create/", views.event_create, name="event_create"),  # ✅ add this
]

