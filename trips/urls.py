from django.urls import path

from .views import (
    # Public / user
    home,
    register,
    my_trips,
    trip_details,

    # Staff-only
    manage_dashboard,
    trip_list,
    trip_create,
    trip_edit,
    trip_delete,
    trip_set_active,
    manage_regs,
    headcount,
    export_regs_csv,
    registration_delete,
)

app_name = "trips"

urlpatterns = [
    # ---------------------- Public / User ----------------------
    path("", home, name="home"),
    path("register/", register, name="register"),
    path("my/", my_trips, name="my"),
    path("trip/details/", trip_details, name="trip-details"),

    # ---------------------- Staff-only -------------------------
    path("manage/", manage_dashboard, name="manage"),

    # Trip CRUD / activation
    path("manage/trips/", trip_list, name="trip-list"),
    path("manage/trips/new/", trip_create, name="trip-create"),
    path("manage/trips/<int:trip_id>/edit/", trip_edit, name="trip-edit"),
    path("manage/trips/<int:trip_id>/delete/", trip_delete, name="trip-delete"),
    path("manage/trips/<int:trip_id>/make-active/", trip_set_active, name="trip-make-active"),

    # Registrations management
    path("manage/registrations/", manage_regs, name="manage-regs"),
    path("manage/registrations/export.csv", export_regs_csv, name="export-regs-csv"),
    path("manage/registrations/<int:reg_id>/delete/", registration_delete, name="reg-delete"),

    # Headcount tool
    path("manage/headcount/", headcount, name="headcount"),
]
