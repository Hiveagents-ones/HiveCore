from fastapi import FastAPI
from .database import engine, Base
from .routers import members, courses, payments, auth, reports
from .core.security import setup_security

app = FastAPI(title="Fitness Club Management")

Base.metadata.create_all(bind=engine)
setup_security(app)

app.include_router(members.router, prefix="/api/v1/members", tags=["members"])
app.include_router(courses.router, prefix="/api/v1/courses", tags=["courses"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
