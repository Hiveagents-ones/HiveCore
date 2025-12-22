from prometheus_client import Counter, Gauge, generate_latest, REGISTRY
from datetime import datetime
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from typing import Optional

# Prometheus metrics
BOOKINGS_TOTAL = Counter(
    'course_bookings_total',
    'Total number of course bookings',
    ['course_id', 'status']
)

CANCELLATION_RATE = Gauge(
    'course_cancellation_rate',
    'Cancellation rate of course bookings',
    ['course_id']
)

ACTIVE_BOOKINGS = Gauge(
    'course_active_bookings',
    'Number of active bookings per course',
    ['course_id']
)

BOOKING_DURATION = Gauge(
    'course_booking_duration_seconds',
    'Duration between booking and cancellation in seconds',
    ['course_id']
)

BOOKING_TIMES = Gauge(
    'course_booking_times',
    'Timestamps of bookings',
    ['course_id', 'status']
)
    'course_active_bookings',
    'Number of active bookings per course',
    ['course_id']
)

router = APIRouter()

def record_booking(course_id: str, status: str = 'confirmed'):
    """
    Record a new booking in Prometheus metrics
    """
    BOOKINGS_TOTAL.labels(course_id=course_id, status=status).inc()
    
    if status == 'confirmed':
        ACTIVE_BOOKINGS.labels(course_id=course_id).inc()
    elif status == 'cancelled':
        ACTIVE_BOOKINGS.labels(course_id=course_id).dec()
        
    # Update cancellation rate (this would be more accurate with a proper calculation)
    current_rate = CANCELLATION_RATE.labels(course_id=course_id)._value.get()
    if status == 'cancelled':
        CANCELLATION_RATE.labels(course_id=course_id).set(current_rate + 0.1)
    else:
        CANCELLATION_RATE.labels(course_id=course_id).set(max(0, current_rate - 0.05))

@router.get('/metrics')
async def get_metrics():
    """
    Expose Prometheus metrics endpoint
    """
    return Response(
        content=generate_latest(REGISTRY),
        media_type='text/plain'
    )