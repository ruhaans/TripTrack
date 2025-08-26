from django.urls import path
from .views import home, register, headcount, trip_details, my_trips

from .views import manage_dashboard, trip_create, trip_list, trip_edit, trip_delete, registration_delete, trip_set_active, manage_regs, export_regs_csv

app_name = "trips"
urlpatterns = [
    path("", home, name="home"),
    path("register/", register, name="register"),
    path("my/", my_trips, name="my"),
    # path("thanks/", thanks, name="thanks"),

    # staff-only
    path("manage/", manage_dashboard, name="manage"),
    path("manage/trips/", trip_list, name="trip-list"),
    path("manage/trips/new/", trip_create, name="trip-create"),
    path("manage/trips/<int:trip_id>/make-active/", trip_set_active, name="trip-make-active"),
    path("trip/details/", trip_details, name="trip-details"),
    path("manage/trips/<int:trip_id>/edit/", trip_edit, name="trip-edit"), 
    path("manage/trips/<int:trip_id>/delete/", trip_delete, name="trip-delete"),
    path("manage/registrations/", manage_regs, name="manage-regs"),
    path("manage/registrations/export.csv", export_regs_csv, name="export-regs-csv"),
    path("manage/registrations/<int:reg_id>/delete/", registration_delete, name="reg-delete"),

    path("manage/headcount/", headcount, name="headcount"),
]
