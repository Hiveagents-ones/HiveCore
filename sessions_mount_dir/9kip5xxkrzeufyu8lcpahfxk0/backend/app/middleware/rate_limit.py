from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi import status
from datetime import datetime, timedelta
from typing import Dict, Tuple
import time

# In-memory storage for rate limiting
rate_limit_data: Dict[str, Tuple[int, float]] = {}

class RateLimiter:
    """
    Rate limiting middleware to prevent abuse of the booking system.
    Limits the number of booking requests per member in a given time window.
    
    Defaults:
    - 5 requests per minute for booking endpoints
    - 10 requests per minute for schedule endpoints
    """
    
    def __init__(self, max_requests: int = 5, time_window: int = 60, schedule_max_requests: int = 10):
        """
        Initialize rate limiter with default values.
        Args:
            max_requests: Maximum allowed requests in the time window
            time_window: Time window in seconds (default: 60 seconds)
        """
        self.max_requests = max_requests
        self.schedule_max_requests = schedule_max_requests
        self.time_window = time_window
    
    async def __call__(self, request: Request):
        """
        Middleware call method that checks and enforces rate limits.
        """
        # Skip rate limiting for non-booking endpoints
        if not request.url.path.startswith('/api/v1/courses/') or not ('bookings' in request.url.path or 'schedule' in request.url.path or 'book' in request.url.path):
            return None
            
        try:
            # Adjust rate limits based on endpoint type
        is_schedule_endpoint = 'schedule' in request.url.path
        current_max_requests = self.schedule_max_requests if is_schedule_endpoint else self.max_requests
        
        # Get member_id from request (assuming it's in headers or query params)
            member_id = request.headers.get('X-Member-ID') or request.query_params.get('member_id')
            if not member_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Member ID is required")
                
            current_time = time.time()
            
            # Check if member is in rate limit data
            if member_id in rate_limit_data:
                request_count, first_request_time = rate_limit_data[member_id]
                
                # Reset counter if time window has passed
                if current_time - first_request_time > self.time_window:
                    rate_limit_data[member_id] = (1, current_time)
                else:
                    # Increment request count
                    if request_count >= current_max_requests:
                        reset_time = first_request_time + self.time_window
                        remaining = int(reset_time - current_time)
                        headers = {
                            'X-RateLimit-Limit': str(current_max_requests),
                            'X-RateLimit-Remaining': '0',
                            'X-RateLimit-Reset': str(reset_time)
                        }
                        raise HTTPException(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail=f"Too many requests. Please try again in {remaining} seconds.",
                            headers=headers
                        )
                    rate_limit_data[member_id] = (request_count + 1, first_request_time)
            else:
                # First request from this member
                rate_limit_data[member_id] = (1, current_time)
            
            return None
            
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail},
                headers=e.headers
            )
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error"}
            )