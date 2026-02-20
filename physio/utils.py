from datetime import time
from .models import Appointment

# Adjust any time slots you want, but keep it consistent across API + booking
BOOKABLE_TIMES = [
    time(9, 0), time(9, 30),
    time(10, 0), time(10, 30),
    time(11, 0), time(11, 30),
    time(12, 0), time(12, 30),
    time(13, 0), time(13, 30),
    time(14, 0), time(14, 30),
    time(15, 0), time(15, 30),
    time(16, 0), time(16, 30),
]


def allocate_room_number(location, date, time_):
    """
    Returns the first available room number (1..location.room_count) for this location/date/time.
    Returns None if no rooms available.
    """
    booked_rooms = set(
        Appointment.objects.filter(location=location, date=date, time=time_)
        .exclude(room__isnull=True)
        .values_list("room", flat=True)
    )

    for r in range(1, location.room_count + 1):
        if r not in booked_rooms:
            return r

    return None
