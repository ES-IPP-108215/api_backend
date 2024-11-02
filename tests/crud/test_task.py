import pytest
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException, status
from sqlalchemy import create_engine
from datetime import datetime, timedelta
from testcontainers.mysql import MySqlContainer
from models.task import Task as TaskModel
from models.user import User as UserModel
from schemas.task import TaskCreate, TaskUpdate, TaskState
from pydantic import ValidationError
from crud.task import create_task, get_tasks_by_user_id, get_task_by_id, update_task, delete_task_by_id
import logging
from db.database import get_db
from main import app

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Container MySQL para testes
my_sql_container = MySqlContainer(
    "mysql:8.0",
    root_password="root",
    dbname="test_db",
    username="test_user",
    password="test_password",
)

@pytest.fixture(scope="module")
def session():
    """
    This fixture creates a new database session for each test case.
    """
    with my_sql_container as mysql:
        mysql.start()
        engine = create_engine(
            mysql.get_connection_url(),
            pool_pre_ping=True,  # Previne erro de conexão interrompida
            connect_args={"connect_timeout": 10}  # Define um timeout maior
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        UserModel.metadata.create_all(bind=engine)
        TaskModel.metadata.create_all(bind=engine)

        def override_get_db():
            db = SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        yield SessionLocal

        # Remove tabelas e fecha o engine
        TaskModel.metadata.drop_all(bind=engine)
        UserModel.metadata.drop_all(bind=engine)
        engine.dispose()

@pytest.fixture
def test_db(session):
    """
    Creates and yields a database session.
    """
    db = session()
    yield db
    db.close()

@pytest.fixture
def test_user(test_db):
    """
    Creates and yields a test user.
    """
    user = UserModel(
        id="id1",
        given_name="John",
        family_name="Doe",
        username="johndoe",
        email="johndoe@example.com",
    )
    test_db.add(user)
    test_db.commit()
    yield user
    # Limpa as tarefas do usuário e o próprio usuário após o teste
    test_db.query(TaskModel).filter(TaskModel.user_id == user.id).delete()
    test_db.delete(user)
    test_db.commit()

def test_create_task_with_deadline(test_db, test_user):
    """
    Test creating a task with a deadline.
    """
    task = TaskCreate(
        title="Task 1",
        description="Task 1 description",
        deadline=datetime.now() + timedelta(days=1),
        priority="high",
    )

    # Executa a criação da tarefa
    created_task = create_task(task=task, db=test_db, user_id=str(test_user.id))

    # Valida se a tarefa foi criada corretamente
    saved_task = test_db.query(TaskModel).filter(TaskModel.id == created_task.id).first()

    assert saved_task is not None
    assert saved_task.title == "Task 1"
    assert saved_task.description == "Task 1 description"
    assert saved_task.deadline is not None
    assert abs((saved_task.deadline - datetime.now()).days) <= 1
    assert saved_task.state == TaskState.TO_DO
    assert saved_task.priority == "high"

def test_create_task_without_deadline(test_db, test_user: UserModel):
    """
    Test creating a task without a deadline.
    """

    task = TaskCreate(
        title="Task 2",
        description="Task 2 description",
        priority="medium",
    )

    # Executa a criação da tarefa
    created_task = create_task(task=task, db=test_db, user_id=str(test_user.id))

    # Valida se a tarefa foi criada corretamente
    saved_task = test_db.query(TaskModel).filter(TaskModel.id == created_task.id).first()

    assert saved_task is not None
    assert saved_task.title == "Task 2"
    assert saved_task.description == "Task 2 description"
    assert saved_task.deadline is None
    assert saved_task.state == TaskState.TO_DO
    assert saved_task.priority == "medium"

def test_create_task_with_deadline_past(test_db, test_user: UserModel):
    """
    Test creating a task with a deadline in the past.
    """

    task = TaskCreate(
        title="Task 3",
        description="Task 3 description",
        deadline=datetime.now() - timedelta(days=1),
        priority="low",
    )

    with pytest.raises(ValueError, match="The deadline cannot be in the past."):
        create_task(task=task, db=test_db, user_id=str(test_user.id))

def test_create_task_without_title(test_db, test_user):
    """
    Test creating a task without a title, which should raise a ValueError.
    """
    task = TaskCreate(
        title="",
        description="Task without a title",
        deadline=datetime.now() + timedelta(days=1),
        priority="low",
    )

    with pytest.raises(ValueError, match="The task must have a title."):
        create_task(task=task, db=test_db, user_id=str(test_user.id))

def test_get_tasks_by_user_id(test_db, test_user):
    """
    Test retrieving all tasks for a given user.
    """
    # Criação de duas tarefas para o usuário de teste
    task1 = TaskCreate(
        title="User Task 1",
        description="Description for User Task 1",
        deadline=datetime.now() + timedelta(days=1),
        priority="high",
    )
    task2 = TaskCreate(
        title="User Task 2",
        description="Description for User Task 2",
        priority="medium",
    )
    create_task(task=task1, db=test_db, user_id=str(test_user.id))
    create_task(task=task2, db=test_db, user_id=str(test_user.id))

    # Recupera todas as tarefas do usuário
    tasks = get_tasks_by_user_id(user_id=str(test_user.id), db=test_db)

    assert len(tasks) == 2

def test_get_task_by_id(test_db, test_user):
    """
    Test retrieving a specific task by its ID.
    """
    # Criação de uma nova tarefa
    task_data = TaskCreate(
        title="Unique Task",
        description="Task to be retrieved by ID",
        deadline=datetime.now() + timedelta(days=1),
        priority="high",
    )
    created_task = create_task(task=task_data, db=test_db, user_id=str(test_user.id))

    # Recupera a tarefa pelo ID
    retrieved_task = get_task_by_id(task_id=created_task.id, db=test_db)

    assert retrieved_task is not None
    assert retrieved_task.title == "Unique Task"
    assert retrieved_task.description == "Task to be retrieved by ID"

def test_get_task_by_invalid_id(test_db):
    """
    Test retrieving a task with a non-existent ID, which should raise a ValueError.
    """
    invalid_task_id = "non_existent_task_id"

    with pytest.raises(ValueError, match="Task not found."):
        get_task_by_id(task_id=invalid_task_id, db=test_db)

def test_update_task_with_new_data(test_db, test_user):
    """
    Test updating a task with new data.
    """
    # Criação de uma nova tarefa
    task_data = TaskCreate(
        title="Original Task",
        description="Original description",
        deadline=datetime.now() + timedelta(days=1),
        priority="medium",
    )
    created_task = create_task(task=task_data, db=test_db, user_id=str(test_user.id))


    # Dados de atualização
    update_data = TaskUpdate(
        title="Updated Task",
        description="Updated description",
        deadline=datetime.now() + timedelta(days=2),
        priority="high",
        state=TaskState.IN_PROGRESS
    )

    # Atualiza a tarefa
    updated_task = update_task(task_id=created_task.id, task=update_data, db=test_db)

    assert updated_task is not None, "Task update failed"
    assert updated_task.title == "Updated Task"
    assert updated_task.description == "Updated description"
    assert updated_task.priority == "high"
    assert updated_task.state == TaskState.IN_PROGRESS
    assert updated_task.deadline is not None, "Deadline should not be None"
    assert abs((updated_task.deadline - datetime.now()).days) <= 2  # Verifica o deadline com margem de 2 dias

def test_update_task_with_past_deadline(test_db, test_user):
    """
    Test updating a task with a past deadline.
    """
    # Criação de uma nova tarefa
    task_data = TaskCreate(
        title="Task with Future Deadline",
        description="Description",
        deadline=datetime.now() + timedelta(days=1),
        priority="medium",
    )
    created_task = create_task(task=task_data, db=test_db, user_id=str(test_user.id))

    # Dados de atualização com deadline no passado
    update_data = TaskUpdate(
        deadline=datetime.now() - timedelta(days=1)
    )

    # Testa se ValueError é levantado
    with pytest.raises(ValueError, match="The deadline cannot be in the past."):
        update_task(task_id=created_task.id, task=update_data, db=test_db)

def test_update_task_without_title(test_db, test_user):
    """
    Test updating a task without a title, which should raise a ValueError.
    """
    # Criação de uma nova tarefa
    task_data = TaskCreate(
        title="Original Task",
        description="Original description",
        deadline=datetime.now() + timedelta(days=1),
        priority="low",
    )
    created_task = create_task(task=task_data, db=test_db, user_id=str(test_user.id))

    # Dados de atualização sem título
    update_data = TaskUpdate(
        title=""
    )

    # Testa se ValueError é levantado
    with pytest.raises(ValueError, match="The task must have a title."):
        update_task(task_id=created_task.id, task=update_data, db=test_db)

def test_update_task_with_invalid_timezone(test_db, test_user):
    """
    Test updating a task with an invalid timezone, which should raise a ValueError.
    """
    # Criação de uma nova tarefa
    task_data = TaskCreate(
        title="Original Task",
        description="Original description",
        deadline=datetime.now() + timedelta(days=1),
        priority="low",
    )
    created_task = create_task(task=task_data, db=test_db, user_id=str(test_user.id))

    # Dados de atualização com timezone inválido
    update_data = TaskUpdate(
        title="Updated Task"
    )

    # Testa se ValueError é levantado
    with pytest.raises(ValueError, match="Invalid timezone."):
        update_task(task_id=created_task.id, task=update_data, db=test_db, timezone="invalid_timezone")

def test_update_task_with_invalid_state(test_db, test_user):
    """
    Test updating a task with an invalid state, which should raise a ValidationError.
    """
    # Criação de uma nova tarefa
    task_data = TaskCreate(
        title="Task for Invalid State Test",
        description="This task will test invalid state handling",
        deadline=datetime.now() + timedelta(days=1),
        priority="medium",
    )
    created_task = create_task(task=task_data, db=test_db, user_id=str(test_user.id))

    # Dados de atualização com estado inválido
    update_data = {
        "state": "invalid_state"  # Estado inválido
    }

    # Testa se ValidationError é levantado ao tentar definir um estado inválido
    with pytest.raises(ValidationError) as exc_info:
        update_task(task_id=created_task.id, task=TaskUpdate(**update_data), db=test_db)

    assert "Input should be 'to_do', 'in_progress' or 'done'" in str(exc_info.value)

def test_delete_task_success(test_db, test_user):
    """
    Test successful deletion of a task.
    """
    # Criação da tarefa
    task_data = TaskCreate(
        title="Task to be deleted",
        description="This task will be deleted in the test",
        deadline=datetime.now() + timedelta(days=1),
        priority="medium",
    )
    created_task = create_task(task=task_data, db=test_db, user_id=str(test_user.id))

    # Deletar a tarefa
    delete_successful = delete_task_by_id(task_id=created_task.id, db=test_db)

    # Verificar se a tarefa foi excluída
    assert delete_successful is True
    assert test_db.query(TaskModel).filter(TaskModel.id == created_task.id).first() is None

def test_delete_task_not_found(test_db):
    """
    Test deletion of a task that does not exist.
    """
    non_existent_task_id = "non_existent_task_id"
    with pytest.raises(HTTPException) as exc_info:
        delete_task_by_id(task_id=non_existent_task_id, db=test_db)

    # Verifica se a exceção capturada é 404
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "Task not found."