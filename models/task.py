from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
import datetime
import uuid

from db.database import Base

class Task(Base):
    """
    Task model class
    """

    __tablename__ = 'tasks'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String)
    description = Column(String)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    priority = Column(String, default='low')  # low, medium, high
    deadline = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), 
        index=True,
        default=datetime.datetime.now, 
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), 
        index=True,
        default=datetime.datetime.now, 
        onupdate=datetime.datetime.now, 
        nullable=False
    )
    state = Column(String, default='to_do')  # to_do, in_progress, done

    def __repr__(self):
        return f'<Task {self.title}>'