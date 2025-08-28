from __future__ import annotations

import csv
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.timezone import now
from django.views.decorators.http import require_http_methods, require_POST
from django.db import transaction
from .forms import RegistrationAdminForm, RegistrationForm, TripForm
from .models import Registration, Trip


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _active_trip() -> Trip | None:
    """Return the single active trip (latest if multiple are active by mistake)."""
    return Trip.objects.filter(is_active=True).order_by("-date").first()


def _is_staff(user) -> bool:
    return user.is_authenticated and user.is_staff


def _seats_taken(trip: Trip) -> int:
    """Robust if related_name exists or not."""
    try:
        return trip.registrations.count()
    except Exception:
        return Registration.objects.filter(trip=trip).count()


def _seats_left(trip: Trip) -> int:
    return max(trip.capacity - _seats_taken(trip), 0)


def _is_full(trip: Trip) -> bool:
    # Prefer model property if present; fallback to local calc
    return getattr(trip, "is_full", None) is True or _seats_left(trip) <= 0


# ---------------------------------------------------------------------
# Public / User pages
# ---------------------------------------------------------------------

from datetime import datetime, time, timedelta
from django.utils import timezone


def home(request):
    """
    Show:
    - Normal public landing if no active trip.
    - Member landing (countdown, what to bring, etc.) if the user is registered
      for the active trip, up to trip.date + 1 day (inclusive).
    """
    trip = _active_trip()

    if not trip:
        return render(
            request,
            "home.html",
            {
                "title": "TripTrack Home",
                "active_trip": None,
            },
        )

    if request.user.is_authenticated:
        reg = (
            Registration.objects.filter(trip=trip, user=request.user)
            .select_related("trip")
            .first()
        )
        if reg:
            today = timezone.localdate()
            cutoff = trip.date + timedelta(days=1)  # visible until next day
            if today <= cutoff:
                ctx = {
                    "title": "My Trip",
                    "trip": trip,
                    "registration": reg,
                    # For countdown JS: pass a proper datetime, falling back to midnight
                    "trip_start_iso": timezone.make_aware(
                        datetime.combine(
                            trip.date, getattr(trip, "meetup_time", time(0))
                        )
                    ).isoformat(),
                }
                return render(request, "trips/home_member.html", ctx)

    # Default: public home
    return render(
        request,
        "home.html",
        {
            "title": "TripTrack Home",
            "active_trip": trip,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def register(request):
    """
    Join the current active trip.
    - Requires verified email
    - Prevents duplicate registration
    - Enforces capacity (race-safe)
    - Snapshots the email used at join time
    - Updates Profile for future prefills (does NOT alter this registration later)
    - Sends confirmation emails (user + organizer)
    """
    # 1) Must be verified
    if not getattr(request.user, "email_verified", False):
        messages.error(request, "Please verify your email to join this trip.")
        return redirect("accounts:resend-verification")

    # 2) Require active trip
    trip = _active_trip()
    if not trip:
        messages.error(request, "Registrations will open soon. No active trip right now.")
        return redirect("trips:home")

    # 3) Already registered? → My Trips
    if Registration.objects.filter(trip=trip, user=request.user).exists():
        return redirect("trips:my")

    # 4) Capacity check (pre-form)
    if _is_full(trip):
        messages.error(request, "Sorry, this trip is full.")
        return redirect("trips:home")

    # Prefill from Profile / User for nicer UX
    profile = getattr(request.user, "profile", None)
    initial = {}
    if profile:
        initial = {
            "first_name": profile.first_name or request.user.first_name or "",
            "last_name":  profile.last_name  or request.user.last_name  or "",
            "phone":      profile.phone_number or "",
            "dob":        profile.date_of_birth or None,
        }
    else:
        initial = {
            "first_name": request.user.first_name or "",
            "last_name":  request.user.last_name or "",
        }

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            # 5) Capacity check again right before saving (race safety)
            trip.refresh_from_db()
            if _is_full(trip):
                messages.error(request, "Sorry, the last seat was just taken.")
                return redirect("trips:home")

            with transaction.atomic():
                # Save registration (form composes full_name for us)
                reg = form.save(commit=False)
                reg.trip = trip
                reg.user = request.user
                reg.email_used = request.user.email  # snapshot the email used now
                reg.save()

                # Update Profile (and mirror to User names) for future prefills
                fn = form.cleaned_data["first_name"].strip()
                ln = form.cleaned_data["last_name"].strip()
                ph = form.cleaned_data["phone"]
                db = form.cleaned_data["dob"]

                changed_user_fields = []
                if request.user.first_name != fn:
                    request.user.first_name = fn
                    changed_user_fields.append("first_name")
                if request.user.last_name != ln:
                    request.user.last_name = ln
                    changed_user_fields.append("last_name")
                if changed_user_fields:
                    request.user.save(update_fields=changed_user_fields)

                if profile:
                    p_changed = False
                    if profile.first_name != fn:
                        profile.first_name = fn; p_changed = True
                    if profile.last_name != ln:
                        profile.last_name = ln; p_changed = True
                    if ph and profile.phone_number != ph:
                        profile.phone_number = ph; p_changed = True
                    if db and profile.date_of_birth != db:
                        profile.date_of_birth = db; p_changed = True
                    if p_changed:
                        profile.save()

            # 6) Emails: user + organizer (best-effort)
            try:
                send_mail(
                    subject=f"You're in: {trip.name}",
                    message=(
                        f"Hi {reg.full_name},\n\n"
                        f"You're registered (status: Pending) for {trip.name} on {trip.date}.\n"
                        f"Meetup: {trip.meetup_time} at {trip.pickup_point}\n\n"
                        f"We'll email ticket details once booked.\n\n"
                        f"- TripTrack"
                    ),
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                    recipient_list=[reg.email_used or request.user.email],
                    fail_silently=False,
                )

                if getattr(settings, "EMAIL_HOST_USER", ""):
                    # Organizer heads-up
                    send_mail(
                        subject=f"[TripTrack] New registration: {reg.full_name} → {trip.name}",
                        message=(
                            f"Name: {reg.full_name}\n"
                            f"Email: {reg.email_used or request.user.email}\n"
                            f"Phone: {reg.phone}\n"
                            f"Park: {reg.get_park_choice_display()}\n"
                            f"DOB: {reg.dob}\n"
                            f"Trip: {trip.name} ({trip.date})\n"
                            f"Seats left now: {_seats_left(trip)}"
                        ),
                        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                        recipient_list=[settings.EMAIL_HOST_USER],
                        fail_silently=True,
                    )
            except Exception:
                messages.warning(request, "Registered, but the email could not be sent right now.")

            messages.success(request, f"You’re in {trip.name}! See your trip in My Trips.")
            return redirect("trips:home")
    else:
        form = RegistrationForm(initial=initial)

    return render(
        request,
        "trips/register.html",
        {"form": form, "title": "Register", "trip": trip},
    )

def trip_details(request):
    """Public ‘marketing’ page for the active trip (long-form details)."""
    trip = _active_trip()
    if not trip:
        messages.error(request, "No active trip right now.")
        return redirect("trips:home")
    return render(
        request, "trips/details.html", {"trip": trip, "title": f"{trip.name} · Details"}
    )


@login_required
def my_trips(request):
    regs = (
        Registration.objects.filter(user=request.user)
        .select_related("trip")
        .order_by("-trip__date", "-created_at")
    )

    today = now().date()
    upcoming = [r for r in regs if r.trip and r.trip.date >= today]
    past = [r for r in regs if r.trip and r.trip.date < today]

    active = _active_trip()
    already_in_active = None
    if active:
        already_in_active = regs.filter(trip=active).first()

    ctx = {
        "title": "My Trips",
        "upcoming": upcoming,
        "past": past,
        "active_trip": already_in_active,  # only pass if joined
        "new_trip": active if not already_in_active else None,  # for the banner
    }
    return render(request, "trips/my_trips.html", ctx)


# ---------------------------------------------------------------------
# Staff tools
# ---------------------------------------------------------------------


@user_passes_test(_is_staff)
def manage_dashboard(request):
    trip = _active_trip()
    stats = {}
    recent_regs = []

    if trip:
        q = Registration.objects.filter(trip=trip).select_related("user")
        total = q.count()
        paid = q.filter(status="paid").count() if hasattr(Registration, "status") else 0
        pending = (
            q.filter(status="pending").count() if hasattr(Registration, "status") else 0
        )
        seats_left = _seats_left(trip)
        capacity = trip.capacity or 0
        filled_pct = round(min(total, capacity) / capacity * 100) if capacity > 0 else 0

        stats = {
            "total": total,
            "paid": paid,
            "pending": pending,
            "seats_left": seats_left,
            "filled_pct": filled_pct,
        }
        recent_regs = list(q.order_by("-created_at")[:8])

    return render(
        request,
        "manage/dashboard.html",
        {
            "trip": trip,
            "stats": stats,
            "recent_regs": recent_regs,
            "title": "Organizer",
        },
    )


@user_passes_test(_is_staff)
def trip_list(request):
    trips = Trip.objects.order_by("-date")
    return render(request, "manage/trip_list.html", {"trips": trips, "title": "Trips"})


@user_passes_test(_is_staff)
def trip_create(request):
    if request.method == "POST":
        form = TripForm(request.POST)
        if form.is_valid():
            trip = form.save()
            if trip.is_active:
                # deactivate others; model.save may already do this
                Trip.objects.exclude(pk=trip.pk).update(is_active=False)
            messages.success(request, "Trip created.")
            return redirect("trips:trip-list")
    else:
        form = TripForm()
    return render(request, "manage/trip_form.html", {"form": form, "title": "New Trip"})


@user_passes_test(_is_staff)
@require_http_methods(["POST"])
def trip_set_active(request, trip_id: int):
    trip = get_object_or_404(Trip, pk=trip_id)
    trip.is_active = True
    trip.save()
    Trip.objects.exclude(pk=trip.pk).update(is_active=False)
    messages.success(request, f"‘{trip.name}’ is now active.")
    return redirect("trips:trip-list")


@user_passes_test(_is_staff)
@require_http_methods(["GET", "POST"])
def manage_regs(request):
    trip = _active_trip()
    if not trip:
        messages.error(request, "No active trip.")
        return redirect("trips:manage")

    regs_qs = (
        Registration.objects.filter(trip=trip)
        .select_related("user")
        .order_by("full_name")
    )

    if request.method == "POST":
        updated = 0
        for r in regs_qs:
            form = RegistrationAdminForm(request.POST, prefix=str(r.id), instance=r)
            if form.is_valid() and form.has_changed():
                form.save()
                updated += 1
        messages.success(request, f"Updated {updated} registration(s).")
        return redirect("trips:manage-regs")

    # Build forms for GET
    forms = [RegistrationAdminForm(prefix=str(r.id), instance=r) for r in regs_qs]
    rows = list(zip(regs_qs, forms))

    # Simple stats for the header cards
    total = regs_qs.count()
    capacity = trip.capacity or 0
    delta = total - capacity  # positive = overbooked, negative = seats left
    paid = (
        regs_qs.filter(status="paid").count() if hasattr(Registration, "status") else 0
    )
    pending = (
        regs_qs.filter(status="pending").count()
        if hasattr(Registration, "status")
        else 0
    )
    cancelled = (
        regs_qs.filter(status="cancelled").count()
        if hasattr(Registration, "status")
        else 0
    )

    ctx = {
        "trip": trip,
        "rows": rows,
        "title": "Registrations",
        "total": total,
        "capacity": capacity,
        "delta": delta,
        "paid": paid,
        "pending": pending,
        "cancelled": cancelled,
    }
    return render(request, "manage/registrations.html", ctx)


@user_passes_test(_is_staff)
def export_regs_csv(request):
    trip = _active_trip()
    if not trip:
        return HttpResponseBadRequest("No active trip")

    regs = (
        Registration.objects.filter(trip=trip)
        .select_related("user")
        .order_by("full_name")
    )

    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = (
        f'attachment; filename="{trip.name.replace(" ", "_")}_registrations.csv"'
    )

    writer = csv.writer(resp)
    writer.writerow(
        [
            "Full Name",
            "Email",
            "Phone",
            "DOB",
            "Park Choice",
            "Status",
            "Imagica Transaction",
            "Price",
            "Gift Code",
            "Outbound",
            "Return",
            "Created At",
        ]
    )
    for r in regs:
        writer.writerow(
            [
                r.full_name,
                r.email_used,
                r.phone,
                r.dob,
                r.get_park_choice_display(),
                r.status,
                r.imagica_transaction,
                r.price or "",
                r.gift_code or "",
                "yes" if r.boarded_outbound else "no",
                "yes" if r.boarded_return else "no",
                r.created_at.isoformat(),
            ]
        )
    return resp


@user_passes_test(_is_staff)
@require_http_methods(["GET", "POST"])
def trip_edit(request, trip_id: int):
    trip = get_object_or_404(Trip, pk=trip_id)
    if request.method == "POST":
        form = TripForm(request.POST, instance=trip)
        if form.is_valid():
            updated = form.save()
            # If marked active, ensure others are inactive
            if updated.is_active:
                Trip.objects.exclude(pk=updated.pk).update(is_active=False)
            messages.success(request, "Trip updated.")
            return redirect("trips:trip-list")
    else:
        form = TripForm(instance=trip)
    return render(
        request,
        "manage/trip_form.html",
        {"form": form, "title": f"Edit Trip · {trip.name}"},
    )


@user_passes_test(_is_staff)
@require_POST
def trip_delete(request, trip_id: int):
    trip = get_object_or_404(Trip, pk=trip_id)
    name = trip.name
    trip.delete()
    messages.success(request, f"Trip “{name}” deleted.")
    return redirect("trips:trip-list")


# ----------------------------- Headcount ------------------------------

# your_app/views.py

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.mail import send_mail
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import urlencode
from django.views.decorators.http import require_http_methods

# ... (assuming your _active_trip and _is_staff functions are here)
# ... (assuming your Registration model is imported)

# your_app/views.py

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.mail import send_mail
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import urlencode
from django.views.decorators.http import require_http_methods

# ... (assuming your _active_trip and _is_staff functions are here)
# ... (assuming your Registration model is imported)

# your_app/views.py

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.mail import send_mail
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import urlencode
from django.views.decorators.http import require_http_methods

# ... (your model imports and helper functions)


from urllib.parse import urlencode

@user_passes_test(_is_staff)
@require_http_methods(["GET", "POST"])
def headcount(request):
    trip = _active_trip()
    if not trip:
        messages.error(request, "No active trip right now.")
        return redirect("trips:home")

    # ----- controls -----
    if request.method == "POST":
        # echo hidden inputs from the form
        mode = (request.POST.get("mode") or "out").lower()
        q = (request.POST.get("q") or "").strip()
        order = request.POST.get("order") or "name_asc"
        only = request.POST.get("only") or ""
    else:
        mode = (request.GET.get("mode") or "out").lower()
        q = (request.GET.get("q") or "").strip()
        order = request.GET.get("order") or "name_asc"
        only = request.GET.get("only") or ""

    if mode not in ("out", "ret"):
        mode = "out"

    # ----- base queryset (only pending/paid show up) -----
    regs_qs = (
        Registration.objects
        .filter(trip=trip, status__in=["pending", "paid"])
        .select_related("user")
    )

    # search
    if q:
        regs_qs = regs_qs.filter(
            Q(full_name__icontains=q) |
            Q(user__email__icontains=q) |
            Q(phone__icontains=q)
        )

    # only unchecked for current mode
    if only == "unchecked":
        regs_qs = regs_qs.filter(
            boarded_outbound=False if mode == "out" else Q(boarded_return=False)
        )

    # sort and snapshot visible rows
    regs_qs = regs_qs.order_by("-full_name" if order == "name_desc" else "full_name")
    regs = list(regs_qs)

    # totals (overall header)
    all_qs = Registration.objects.filter(trip=trip, status__in=["pending", "paid"])
    totals_all = {
        "total": all_qs.count(),
        "outbound": all_qs.filter(boarded_outbound=True).count(),
        "return": all_qs.filter(boarded_return=True).count(),
    }

    # totals (shown for this mode)
    def count_checked_visible(rs):
        if mode == "out":
            return sum(1 for r in rs if r.boarded_outbound)
        return sum(1 for r in rs if r.boarded_return)

    totals_shown = {"total": len(regs), "checked": count_checked_visible(regs)}

    if request.method == "POST":
        updated = 0
        emailed = 0

        for r in regs:  # only update rows being viewed/filtered
            key = f"{'out' if mode == 'out' else 'ret'}-{r.id}"
            new_val = (request.POST.get(key) == "on")

            if mode == "out":
                send_email = (not r.boarded_outbound) and new_val
                if new_val != r.boarded_outbound:
                    r.boarded_outbound = new_val
                    r.save(update_fields=["boarded_outbound"])
                    updated += 1
                    if send_email and r.user and r.user.email:
                        try:
                            send_mail(
                                subject=f"You're on board — {trip.name}",
                                message=(
                                    f"Hi {r.full_name},\n\n"
                                    f"We have marked you as seated on the bus for the {trip.name} trip.\n\n"
                                    f"⚠ Please remain in the bus until further instructions from the organizers.\n"
                                    f"Do not get down without our permission for safety and coordination reasons.\n\n"
                                    f"Have a great journey ahead!\n"
                                    f"- TripTrack Organizing Team"
                                ),
                                from_email=settings.DEFAULT_FROM_EMAIL,
                                recipient_list=[r.user.email],
                                fail_silently=True,
                            )
                            emailed += 1
                        except Exception:
                            pass
            else:  # mode == 'ret'
                send_email = (not r.boarded_return) and new_val
                if new_val != r.boarded_return:
                    r.boarded_return = new_val
                    r.save(update_fields=["boarded_return"])
                    updated += 1
                    if send_email and r.user and r.user.email:
                        try:
                            send_mail(
                                subject=f"Return boarding confirmed — {trip.name}",
                                message=(
                                    f"Hi {r.full_name},\n\n"
                                    f"You are now checked in for the return journey of the {trip.name} trip.\n\n"
                                    f"⚠ Please stay in the bus until we arrive at the designated drop point.\n"
                                    f"Do not get down without organizer approval.\n\n"
                                    f"We hope you had a wonderful time!\n"
                                    f"- TripTrack Organizing Team"
                                ),
                                from_email=settings.DEFAULT_FROM_EMAIL,
                                recipient_list=[r.user.email],
                                fail_silently=True,
                            )
                            emailed += 1
                        except Exception:
                            pass

        messages.success(request, f"Saved {updated} record(s). Sent {emailed} email(s).")

        # preserve filters on redirect
        params = {"mode": mode}
        if q:
            params["q"] = q
        if order and order != "name_asc":
            params["order"] = order
        if only == "unchecked":
            params["only"] = only
        suffix = ("?" + urlencode(params)) if params else ""
        return redirect(f"{reverse('trips:headcount')}{suffix}")

    # GET
    return render(
        request,
        "trips/headcount.html",
        {
            "title": "Headcount",
            "trip": trip,
            "regs": regs,
            "mode": mode,
            "q": q,
            "order": order,
            "only": only,
            "totals_all": totals_all,
            "totals_shown": totals_shown,
        },
    )


# --------------------------- Registrations ----------------------------


@user_passes_test(_is_staff)
@require_POST
def registration_delete(request, reg_id: int):
    trip = _active_trip()
    if not trip:
        messages.error(request, "No active trip.")
        return redirect("trips:manage-regs")

    reg = get_object_or_404(Registration, pk=reg_id, trip=trip)
    who = f"{reg.full_name} <{reg.user.email}>"
    reg.delete()
    messages.success(request, f"Deleted participant: {who}")
    return redirect("trips:manage-regs")
