# trips/models.py
from django.conf import settings
from django.db import models
from django.db.models import Q, UniqueConstraint


class Trip(models.Model):
    name = models.CharField(max_length=120)
    date = models.DateField()
    meetup_time = models.TimeField()
    return_time = models.TimeField(null=True, blank=True)
    pickup_point = models.CharField(max_length=200)
    capacity = models.PositiveIntegerField(default=50)
    is_active = models.BooleanField(default=True)
    details = models.TextField(blank=True)

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.CheckConstraint(check=Q(capacity__gte=0), name="trip_capacity_nonnegative"),
            # ensures at most one active trip; remove if you want multiple actives
            # UniqueConstraint(fields=[], condition=Q(is_active=True), name="only_one_active_trip"),
        ]

    @property
    def seats_taken(self) -> int:
        # use related_name on Registration to avoid N+1 later
        return self.registrations.count()

    @property
    def seats_left(self) -> int:
        return max(self.capacity - self.seats_taken, 0)

    @property
    def is_full(self) -> bool:
        return self.seats_left <= 0

    def __str__(self):
        return f"{self.name} ({self.date})"


PARK_CHOICES = [
    ("theme", "Theme Park"),
    ("water", "Water Park"),
]

STATUS = [
    ("pending", "Pending"),
    ("confirmed", "Confirmed"),
    ("cancelled", "Cancelled"),
]


class Registration(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="registrations")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="registrations")

    # SNAPSHOT FIELDS (don’t auto-update)
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20)
    dob = models.DateField()
    park_choice = models.CharField(max_length=10, choices=PARK_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS, default="pending")

    # NEW: email snapshot at time of registration
    email_used = models.EmailField(null=True, blank=True)

    imagica_transaction = models.CharField(max_length=120, blank=True)
    boarded_outbound = models.BooleanField(default=False)
    boarded_return = models.BooleanField(default=False)

    price = models.PositiveIntegerField(null=True, blank=True)
    gift_code = models.CharField(max_length=50, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("trip", "user")]
        ordering = ["full_name"]
        indexes = [
            models.Index(fields=["trip", "full_name"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.full_name} → {self.trip.name}"