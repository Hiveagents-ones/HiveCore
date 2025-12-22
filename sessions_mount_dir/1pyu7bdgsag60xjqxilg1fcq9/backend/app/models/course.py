from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from .database import Base


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    time = Column(DateTime, nullable=False)
    coach_id = Column(Integer, ForeignKey("coaches.id"), nullable=False)

    coach = relationship("Coach", back_populates="courses")

    def __repr__(self):
        return f"<Course(id={self.id}, name='{self.name}', time='{self.time}')>"