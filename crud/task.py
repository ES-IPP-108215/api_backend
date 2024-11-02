from typing import Sequence, Optional
import pytz
from datetime import datetime
from dateutil import parser
from fastapi import Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from models.task import Task
from schemas.task import TaskCreate, TaskInDB
from db.database import get_db


def create_task(task: TaskCreate, user_id: str, db: Session = Depends(get_db), timezone: str = "UTC") -> TaskInDB:
    """
    Create a new task for a given user, with validation and error handling.
    """
    try:
        user_tz = pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError:
        raise ValueError("Invalid timezone.")

    # Define timestamps com o timezone do usuário
    now = datetime.now(tz=user_tz)
    task_data = task.model_dump()
    task_data.update({
        'user_id': user_id,
        'created_at': now,
        'updated_at': now,
        'state': 'to_do' 
    })

    if not task.title or task.title.strip() == "":
        raise ValueError("The task must have a title.")
    
    # Verifica e ajusta a deadline para o timezone do usuário
    if task.deadline:
        if isinstance(task.deadline, str):
            try:
                task.deadline = parser.parse(task.deadline)
            except ValueError:
                raise ValueError("The deadline format is invalid.")
        
        if task.deadline.tzinfo is None:
            task.deadline = task.deadline.replace(tzinfo=user_tz)

        if task.deadline < now:
            raise ValueError("The deadline cannot be in the past.")

    db_task = Task(**task_data)
    
    try:
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("Error: Could not create the task due to a database integrity issue.") from exc
    
    return db_task



def get_tasks_by_user_id(user_id: str, db: Session = Depends(get_db)) -> Sequence[TaskInDB]:
    """
    Retrieve all tasks for a given user.
    """
    tasks = db.query(Task).filter(Task.user_id == user_id).all()
    return tasks

def get_task_by_id(task_id: str, db: Session = Depends(get_db)) -> Optional[TaskInDB]:
    """
    Retrieve a task by its unique identifier.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise ValueError("Task not found.")
    return task
