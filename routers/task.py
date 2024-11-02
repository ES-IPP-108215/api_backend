import logging 
from typing import List, Sequence
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.database import get_db
from schemas.task import TaskCreate, TaskInDB, TaskUpdate
from crud.task import create_task, delete_task_by_id, get_tasks_by_user_id, get_task_by_id, update_task
from crud.user import get_user_by_id, get_user
from auth.auth import jwks, get_current_user
from auth.JWTBearer import JWTBearer

router = APIRouter(tags=['tasks'])

auth = JWTBearer(jwks)

@router.post('/tasks', 
             response_model=TaskInDB, 
             status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(auth)],
             )
async def create_new_task(task: TaskCreate,
                          db: Session = Depends(get_db),
                          current_user_username: str = Depends(get_current_user)):
    """
    Create a new task for the authenticated user.
    """
    user = get_user(current_user_username, db=db)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    
    try:
        new_task = create_task(task, user_id=str(user.id), db=db)

        return new_task
    
    except HTTPException as http_exc:
        raise http_exc
    
    except ValueError as val_err:
        logging.error("Error creating task: %s", val_err)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err)) from val_err

    except Exception as exc:
        logging.exception("Unexpected error creating task: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred while creating the task.") from exc

@router.get('/tasks/{task_id}', 
            response_model=TaskInDB,
            status_code=status.HTTP_200_OK,
            dependencies=[Depends(auth)])
async def get_task(task_id: str,
                   db: Session = Depends(get_db),
                   current_user_username: str = Depends(get_current_user)):
    """
    Retrieve a task by its unique identifier for the authenticated user.
    """
    # Log para verificar se o usuário é recuperado corretamente
    user = get_user(current_user_username, db=db)
    if not user:
        logging.error("User not found for username: %s", current_user_username)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    
    try:
        task = get_task_by_id(task_id, db=db)
        if not task:
            logging.error("Task not found with id: %s", task_id)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

        # Log de verificação de permissão de acesso
        logging.info("User ID: %s, Task User ID: %s", user.id, task.user_id)
        if task.user_id != str(user.id):
            logging.warning("User %s is not authorized to access task %s", user.id, task.id)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this task.")

        return task

    except HTTPException as http_exc:
        raise http_exc  # Propaga exceções HTTP específicas já configuradas
    
    except Exception as exc:
        logging.exception("Unexpected error retrieving task: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred while retrieving the task.") from exc



@router.put('/tasks/{task_id}', 
            response_model=TaskInDB,
            status_code=status.HTTP_200_OK,
            dependencies=[Depends(auth)])
async def update_task_route(task_id: str,
                            task: TaskUpdate,
                            db: Session = Depends(get_db),
                            current_user_username: str = Depends(get_current_user),
                            timezone: str = "UTC"):
    """
    Update a task by its unique identifier for the authenticated user.
    """
    user = get_user(current_user_username, db=db)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    
    try:
        db_task = get_task_by_id(task_id, db=db)

        if not db_task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
        
        if db_task.user_id != str(user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this task.")

        updated_task = update_task(task_id, task, db=db, timezone=timezone)
        
        return updated_task
    
    except ValueError as val_err:
        logging.error("Error updating task: %s", val_err)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err)) from val_err

    except HTTPException as http_exc:
        raise http_exc
    
    except Exception as exc:
        logging.exception("Unexpected error updating task: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred while updating the task.") from exc

@router.delete('/tasks/{task_id}',
               status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(auth)])
async def delete_task(task_id: str,
                      db: Session = Depends(get_db),
                      current_user_username: str = Depends(get_current_user)):
    """
    Delete a task by its unique identifier for the authenticated user.
    """
    user = get_user(current_user_username, db=db)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    try:
        task = get_task_by_id(task_id, db=db)
        
        if task.user_id != str(user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this task.")
        
        delete_task_by_id(task_id, db=db)
        return

    except HTTPException as http_exc:
        # Propaga diretamente a HTTPException já configurada
        raise http_exc
    
    except ValueError as val_err:
        logging.error("Task deletion error: %s", val_err)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.") from val_err

    except Exception as exc:
        logging.exception("Unexpected error deleting task: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred while deleting the task.") from exc
