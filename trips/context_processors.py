from .models import Trip

def active_trip(request):
    trip = Trip.objects.filter(is_active=True).order_by("-date").first()
    return {"active_trip": trip}
