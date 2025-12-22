from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import members
from app.routers import courses
from app.routers import bookings
from app.routers import payments
from app.routers import membership
from app.database import engine, init_db
from app.models import member
from app.core.audit import AuditMiddleware

# Initialize database
init_db()

app = FastAPI(
    title="Membership Management System",
    description="API for managing member information",
    version="1.0.0"
)

# Configure CORS
# Add audit middleware
app.add_middleware(AuditMiddleware)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(members.router, prefix="/api/v1/members", tags=["members"])
app.include_router(courses.router, prefix="/api/v1/courses", tags=["courses"])
app.include_router(bookings.router, prefix="/api/v1/bookings", tags=["bookings"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])
app.include_router(membership.router, prefix="/api/v1/membership", tags=["membership"])

@app.get("/")
def read_root():
    return {"message": "Membership Management System API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
