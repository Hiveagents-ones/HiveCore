from fastapi import FastAPI
from api.v1.endpoints import bookings

app = FastAPI()

app.include_router(bookings.router)