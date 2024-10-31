import logging 
from typing import List, Sequence
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.database import get_db
from schemas.task import TaskCreate, TaskInDB, TaskUpdate
from crud.task import create_task, get_tasks_by_user_id, get_task_by_id
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

 


    