from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.routers import members
from app.core.config import settings
from app.database import engine
from app.models import member

# Create database tables
member.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Membership Management System",
    description="API for managing member information",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(members.router, prefix="/api/v1/members", tags=["members"])


@app.get("/")
async def root():
    return {"message": "Membership Management System API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
