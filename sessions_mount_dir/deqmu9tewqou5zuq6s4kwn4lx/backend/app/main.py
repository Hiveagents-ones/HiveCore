from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import courses, bookings, members
from app.database import engine
from app.models import course, member, booking

# Create database tables
course.Base.metadata.create_all(bind=engine)
member.Base.metadata.create_all(bind=engine)
booking.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Gym Course Booking System",
    description="API for gym course booking functionality",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(courses.router, prefix="/api/courses", tags=["courses"])
app.include_router(bookings.router, prefix="/api/bookings", tags=["bookings"])
app.include_router(members.router, prefix="/api/members", tags=["members"])

@app.get("/")
def read_root():
    return {"message": "Gym Course Booking API is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)