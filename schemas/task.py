from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
import uuid

class TaskBase(BaseModel):
    """
    Base model for a task.

    Attributes:
        title (str): The title of the task.
        description (Optional[str]): A description of the task.
        priority (Optional[str]): The priority level of the task. Default is 'low'.
        deadline (Optional[datetime]): The deadline for the task in ISO format.
    """
    title: str = Field(..., description="Example Task")
    description: Optional[str] = Field(None, description="A description of the task")
    priority: Optional[str] = Field('low', description="Priority level: low, medium, high")
    deadline: Optional[datetime] = Field(None, description="Deadline for the task in ISO format, e.g., 2024-12-31T23:59:00")

class TaskCreate(TaskBase):
    """
    Model for creating a new task. Inherits from TaskBase.
    """
    deadline: Optional[datetime] = None
    pass

class TaskUpdate(BaseModel):
    """
    Model for updating an existing task.

    Attributes:
        title (Optional[str]): The title of the task.
        description (Optional[str]): A description of the task.
        priority (Optional[str]): The priority level of the task.
        deadline (Optional[datetime]): The deadline for the task in ISO format.
        state (Optional[str]): The state of the task. Can be 'to_do', 'in_progress', or 'done'.
    """
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    deadline: Optional[datetime] = None
    state: Optional[str] = Field(None, description="State of the task: to_do, in_progress, done")

class TaskInDB(TaskBase):
    """
    Model for a task stored in the database. Inherits from TaskBase.

    Attributes:
        id (str): The unique identifier of the task.
        user_id (str): The ID of the user who created the task.
        created_at (datetime): The timestamp when the task was created.
        updated_at (datetime): The timestamp when the task was last updated.
        state (str): The state of the task. Default is 'to_do'.
        deadline (Optional[datetime]): The deadline for the task in ISO format.
        priority (str): The priority level of the task. Default is 'low'.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    created_at: datetime
    updated_at: datetime
    state: str = "to_do"
    deadline: Optional[datetime] = None
    priority: str = "low"

    model_config = ConfigDict(from_attributes=True)  # Atualização para Pydantic v2
class TaskResponse(TaskInDB):
    """
    Model for the response returned to the client. Inherits from TaskInDB.
    """
    pass