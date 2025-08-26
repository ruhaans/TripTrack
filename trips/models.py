from django.db import models
from django.conf import settings

class Trip(models.Model):
    name = models.CharField(max_length=120)
    date = models.DateField()
    meetup_time = models.TimeField()
    return_time = models.TimeField(null=True, blank=True)
    pickup_point = models.CharField(max_length=200)
    capacity = models.PositiveIntegerField(default=50)
    is_active = models.BooleanField(default=True)

    details = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.date})"
    
    @property
    def seats_taken(self):
        return self.registrations.count()

    @property
    def seats_left(self):
        return max(self.capacity - self.seats_taken, 0)

    @property
    def is_full(self):
        return self.seats_left <= 0

    def save(self, *args, **kwargs):
        # keep "only one active" behavior you added earlier
        super().save(*args, **kwargs)
        if self.is_active:
            Trip.objects.exclude(pk=self.pk).filter(is_active=True).update(is_active=False)

class Registration(models.Model):
    PARK_CHOICES = [("theme","Theme Park"),("water","Water Park")]
    STATUS = [("pending","Pending"),("paid","Paid"),("cancelled","Cancelled")]

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="registrations")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="registrations")
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20)
    dob = models.DateField("Date of Birth")
    park_choice = models.CharField(max_length=10, choices=PARK_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS, default="pending")
    imagica_transaction = models.CharField(max_length=120, blank=True)
    boarded_outbound = models.BooleanField(default=False)
    boarded_return = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    price = models.PositiveIntegerField(null=True, blank=True)   # ₹
    gift_code = models.CharField(max_length=50, null=True, blank=True)
    
    class Meta:
        unique_together = [("trip", "user")]  # one registration per user per trip

    def __str__(self):
        return f"{self.full_name} → {self.trip.name}"
