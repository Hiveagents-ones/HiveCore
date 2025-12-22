from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from .routers import members, courses, trainers, payments
from .database import engine, Base, get_db

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(members.router, prefix="/api/v1", tags=["members"])
app.include_router(courses.router, prefix="/api/v1", tags=["courses"])
app.include_router(trainers.router, prefix="/api/v1", tags=["trainers"])
app.include_router(payments.router, prefix="/api/v1", tags=["payments"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the FastAPI application"}
