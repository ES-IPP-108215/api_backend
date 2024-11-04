from typing import Sequence, Optional
import pytz
from datetime import datetime
from dateutil import parser
from fastapi import Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from models.task import Task
from schemas.task import TaskCreate, TaskInDB, TaskUpdate, TaskState
from db.database import get_db


def create_task(task: TaskCreate, user_id: str, db: Session = Depends(get_db), timezone: str = "UTC") -> TaskInDB:
    """
    Create a new task for a given user, with validation and error handling.
    """
    try:
        user_tz = pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError as exc:
        raise ValueError("Invalid timezone.") from exc

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
        raise ValueError(
            "Error: Could not create the task due to a database integrity issue.") from exc

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


def update_task(task_id: str, task: TaskUpdate, db: Session = Depends(get_db), timezone: str = "UTC") -> Optional[TaskInDB]:
    """
    Update a task by its unique identifier.
    """
    try:
        user_tz = pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError as exc:
        raise ValueError("Invalid timezone.") from exc

    db_task = get_task_by_id(task_id, db)
    now = datetime.now(tz=user_tz)

    # Ignora campos não definidos
    task_data = task.model_dump(exclude_unset=True)
    task_data.update({'updated_at': now})

    # Validação de `title`, se fornecido
    if 'title' in task_data and (not task_data['title'] or task_data['title'].strip() == ""):
        raise ValueError("The task must have a title.")
    
    if 'state' in task_data and task_data['state'] not in TaskState.__members__.values():
        raise ValueError("Invalid task state.")

    # Conversão de `deadline`, se fornecido
    if 'deadline' in task_data and task_data['deadline'] is not None:
        if isinstance(task_data['deadline'], str):
            try:
                task_data['deadline'] = parser.parse(task_data['deadline'])
            except ValueError as exc:
                raise ValueError("The deadline format is invalid.") from exc

        if task_data['deadline'].tzinfo is None:
            task_data['deadline'] = task_data['deadline'].replace(
                tzinfo=user_tz)

        if task_data['deadline'] < now:
            raise ValueError("The deadline cannot be in the past.")

    # Atualiza apenas os campos definidos no `task_data`
    for key, value in task_data.items():
        setattr(db_task, key, value)

    try:
        db.commit()
        db.refresh(db_task)
    except IntegrityError as exc:
        db.rollback()
        raise ValueError(
            "Error: Could not update the task due to a database integrity issue.") from exc

    return db_task

def delete_task_by_id(task_id: str, db: Session = Depends(get_db)) -> bool:
    """
    Delete a task by its unique identifier.
    """
    try:
        db_task = get_task_by_id(task_id, db)
        db.delete(db_task)
        db.commit()
        return True
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.") from val_err

