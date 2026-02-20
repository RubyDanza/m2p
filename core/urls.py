from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),

    path("login/", views.login_view, name="login"),
    path("post-login/", views.post_login, name="post_login"),

    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),

    path("owner/locations/add/", views.location_add, name="location_add"),

    path("owner/locations/<int:location_id>/consultants/", views.location_consultants, name="location_consultants"),


]
