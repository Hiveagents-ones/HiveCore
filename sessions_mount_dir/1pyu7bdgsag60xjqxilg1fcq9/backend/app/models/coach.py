from sqlalchemy import Column, Integer, String, JSON
from sqlalchemy.orm import relationship

from .database import Base


class Coach(Base):
    __tablename__ = "coaches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    schedule = Column(JSON, nullable=True, default={"work_days": [], "shifts": []})

    courses = relationship("Course", back_populates="coach")