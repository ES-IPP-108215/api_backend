import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import datetime
from main import app
from db.database import get_db
from routers.task import auth
from schemas.task import TaskResponse, TaskState
from auth.auth import get_current_user
from auth.JWTBearer import JWTAuthorizationCredentials, JWTBearer

client = TestClient(app)

# Credenciais JWT mockadas
credentials = JWTAuthorizationCredentials(
    jwt_token="valid_token",
    header={"kid": "kid"},
    claims={"sub": "sub"},
    signature="signature",
    message="message",
)

@pytest.fixture(scope="module")
def mock_db():
    # Mock do banco de dados
    db = MagicMock(spec=Session)
    app.dependency_overrides[get_db] = lambda: db
    yield db

@pytest.fixture(autouse=True)
def reset_mock_db(mock_db):
    # Reseta o mock do banco de dados após cada teste
    mock_db.reset_mock()

@patch("routers.task.get_user")
@patch("routers.task.create_task")  # Mock da função create_task
@patch.object(
    JWTBearer, "__call__", return_value=credentials  # Mock do JWT para autorizar
)
def test_create_new_task(
    mock_jwt_bearer,
    mock_create_task,
    mock_get_user,
    mock_db,
):
    app.dependency_overrides[auth] = lambda: credentials
    app.dependency_overrides[get_current_user] = lambda: "username1"

    headers = {"Authorization": "Bearer token"}

    # Dados de exemplo para a tarefa
    new_task_data = {
        "title": "Test Task",
        "description": "This is a test task",
        "deadline": (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat(),  # Converte para ISO
        "priority": "medium",
    }

    # Dados da resposta simulada
    mock_task_response = TaskResponse(
        id="task_id_123",
        user_id="user_id_456",
        title="Test Task",
        description="This is a test task",
        deadline=datetime.datetime.now() + datetime.timedelta(days=1),
        priority="medium",
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
        state=TaskState.TO_DO,
    )

    # Configuração dos mocks
    mock_user = MagicMock()
    mock_user.id = "user_id_456"
    mock_get_user.return_value = mock_user
    mock_create_task.return_value = mock_task_response

    # Faz a requisição de criação da nova tarefa
    response = client.post(
        "/tasks",
        json=new_task_data,
        headers=headers,
    )

    # Valida a resposta
    assert response.status_code == 201
    assert response.json()["title"] == "Test Task"
    assert response.json()["description"] == "This is a test task"
    assert response.json()["priority"] == "medium"
    assert response.json()["state"] == TaskState.TO_DO.value

    app.dependency_overrides = {}


@patch("routers.task.get_user")
@patch("routers.task.create_task")
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_create_task_user_not_found(mock_jwt_bearer, mock_create_task, mock_get_user, mock_db):
    """
    Testa o erro 404 quando o usuário não é encontrado.
    """
    mock_get_user.return_value = None  # Simula usuário não encontrado

    new_task_data = {
        "title": "Test Task",
        "description": "This is a test task",
        "deadline": (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat(),
        "priority": "medium",
    }

    response = client.post("/tasks", json=new_task_data, headers={"Authorization": "Bearer valid_token"})
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "User not found."

@patch("routers.task.get_user")
@patch("routers.task.create_task")
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_create_task_value_error(mock_jwt_bearer, mock_create_task, mock_get_user, mock_db):
    """
    Testa o erro 400 quando ocorre um ValueError.
    """
    mock_user = MagicMock()
    mock_user.id = "user_id_123"
    mock_get_user.return_value = mock_user

    # Configura create_task para lançar ValueError
    mock_create_task.side_effect = ValueError("Invalid task data")

    new_task_data = {
        "title": "Test Task",
        "description": "This is a test task",
        "deadline": (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat(),
        "priority": "medium",
    }

    response = client.post("/tasks", json=new_task_data, headers={"Authorization": "Bearer valid_token"})
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Invalid task data"

@patch("routers.task.get_user")
@patch("routers.task.create_task")
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_create_task_unexpected_error(mock_jwt_bearer, mock_create_task, mock_get_user, mock_db):
    """
    Testa o erro 500 quando ocorre uma Exception inesperada.
    """
    mock_user = MagicMock()
    mock_user.id = "user_id_123"
    mock_get_user.return_value = mock_user

    # Configura create_task para lançar uma Exception genérica
    mock_create_task.side_effect = Exception("Unexpected error")

    new_task_data = {
        "title": "Test Task",
        "description": "This is a test task",
        "deadline": (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat(),
        "priority": "medium",
    }

    response = client.post("/tasks", json=new_task_data, headers={"Authorization": "Bearer valid_token"})
    
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json()["detail"] == "An error occurred while creating the task."


@patch("routers.task.get_user")
@patch("routers.task.get_task_by_id")
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_get_task_by_id_success(mock_jwt_bearer, mock_get_task_by_id, mock_get_user):
    """
    Testa a recuperação bem-sucedida de uma tarefa.
    """
    mock_user = MagicMock()
    mock_user.id = "user_id_123"
    mock_get_user.return_value = mock_user

    task_data = TaskResponse(
        id="task_id_123",
        user_id="user_id_123",
        title="Sample Task",
        description="Sample Description",
        deadline=datetime.datetime.now() + datetime.timedelta(days=1),
        priority="high",
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
        state=TaskState.TO_DO,
    )
    mock_get_task_by_id.return_value = task_data

    response = client.get("/tasks/task_id_123", headers={"Authorization": "Bearer valid_token"})
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == "task_id_123"
    assert response.json()["title"] == "Sample Task"

@patch("routers.task.get_user")
@patch("routers.task.get_task_by_id")
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_get_task_user_not_found(mock_jwt_bearer, mock_get_task_by_id, mock_get_user):
    """
    Testa o erro 404 quando o usuário não é encontrado.
    """
    mock_get_user.return_value = None  # Simula usuário não encontrado

    response = client.get("/tasks/task_id_123", headers={"Authorization": "Bearer valid_token"})
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "User not found."

@patch("routers.task.get_user")
@patch("routers.task.get_task_by_id")
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_get_task_not_found(mock_jwt_bearer, mock_get_task_by_id, mock_get_user):
    """
    Testa o erro 404 quando a tarefa não é encontrada.
    """
    mock_user = MagicMock()
    mock_user.id = "user_id_123"
    mock_get_user.return_value = mock_user

    # Simula tarefa não encontrada retornando None
    mock_get_task_by_id.return_value = None

    response = client.get("/tasks/non_existent_task_id", headers={"Authorization": "Bearer valid_token"})
    
    # Verifica se a resposta é 404 Not Found
    assert response.status_code == status.HTTP_404_NOT_FOUND, f"Esperado status 404, mas obteve {response.status_code}."
    assert response.json()["detail"] == "Task not found."

@patch("routers.task.get_user")
@patch("routers.task.get_task_by_id")
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_get_task_forbidden(mock_jwt_bearer, mock_get_task_by_id, mock_get_user):
    """
    Testa o erro 403 quando o usuário não tem permissão para acessar a tarefa.
    """
    # Configura mock para usuário autenticado
    mock_user = MagicMock()
    mock_user.id = "user_id_123"  # ID do usuário autenticado
    mock_get_user.return_value = mock_user

    # Configura mock para tarefa pertencente a outro usuário
    task_data = TaskResponse(
        id="task_id_123",
        user_id="another_user_id",  # ID de outro usuário
        title="Sample Task",
        description="Sample Description",
        deadline=datetime.datetime.now() + datetime.timedelta(days=1),
        priority="high",
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
        state=TaskState.TO_DO,
    )
    mock_get_task_by_id.return_value = task_data

    # Envia a requisição GET para recuperar a tarefa
    response = client.get("/tasks/task_id_123", headers={"Authorization": "Bearer valid_token"})
    
    # Verifica o status esperado
    assert response.status_code == status.HTTP_403_FORBIDDEN, f"Esperado status 403, mas obteve {response.status_code}."
    assert response.json()["detail"] == "Not authorized to access this task."


@patch("routers.task.get_user")
@patch("routers.task.get_task_by_id")
@patch("routers.task.update_task")
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_update_task_success(mock_jwt_bearer, mock_update_task, mock_get_task_by_id, mock_get_user):
    """
    Testa a atualização bem-sucedida de uma tarefa.
    """
    mock_user = MagicMock()
    mock_user.id = "user_id_123"
    mock_get_user.return_value = mock_user

    existing_task = TaskResponse(
        id="task_id_123",
        user_id="user_id_123",
        title="Sample Task",
        description="Sample Description",
        deadline=datetime.datetime.now() + datetime.timedelta(days=1),
        priority="high",
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
        state=TaskState.TO_DO,
    )
    mock_get_task_by_id.return_value = existing_task

    updated_task = existing_task.model_copy()
    updated_task.title = "Updated Task"
    mock_update_task.return_value = updated_task

    update_data = {"title": "Updated Task"}

    response = client.put("/tasks/task_id_123", json=update_data, headers={"Authorization": "Bearer valid_token"})
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["title"] == "Updated Task"

@patch("routers.task.get_user")
@patch("routers.task.update_task")
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_update_task_user_not_found(mock_jwt_bearer, mock_update_task, mock_get_user):
    """
    Testa o erro 404 quando o usuário não é encontrado.
    """
    mock_get_user.return_value = None  # Simula usuário não encontrado

    update_data = {"title": "Updated Task"}

    response = client.put("/tasks/task_id_123", json=update_data, headers={"Authorization": "Bearer valid_token"})
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "User not found."

@patch("routers.task.get_user")
@patch("routers.task.get_task_by_id")
@patch("routers.task.update_task")
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_update_task_not_found(mock_jwt_bearer, mock_update_task, mock_get_task_by_id, mock_get_user):
    """
    Testa o erro 404 quando a tarefa não é encontrada.
    """
    mock_user = MagicMock()
    mock_user.id = "user_id_123"
    mock_get_user.return_value = mock_user

    mock_get_task_by_id.return_value = None

    update_data = {"title": "Updated Task"}

    response = client.put("/tasks/non_existent_task_id", json=update_data, headers={"Authorization": "Bearer valid_token"})
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Task not found."

@patch("routers.task.get_user")
@patch("routers.task.get_task_by_id")
@patch("routers.task.update_task")
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_update_task_forbidden(mock_jwt_bearer, mock_update_task, mock_get_task_by_id, mock_get_user):
    """
    Testa o erro 403 quando o usuário não tem permissão para atualizar a tarefa.
    """
    mock_user = MagicMock()
    mock_user.id = "user_id_123"
    mock_get_user.return_value = mock_user

    existing_task = TaskResponse(
        id="task_id_123",
        user_id="another_user_id",  # Usuário diferente
        title="Sample Task",
        description="Sample Description",
        deadline=datetime.datetime.now() + datetime.timedelta(days=1),
        priority="high",
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
        state=TaskState.TO_DO,
    )
    mock_get_task_by_id.return_value = existing_task

    update_data = {"title": "Updated Task"}

    response = client.put("/tasks/task_id_123", json=update_data, headers={"Authorization": "Bearer valid_token"})
    
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "Not authorized to update this task."

@patch("routers.task.get_user")
@patch("routers.task.get_task_by_id")
@patch("routers.task.update_task")
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_update_task_value_error(mock_jwt_bearer, mock_update_task, mock_get_task_by_id, mock_get_user):
    """
    Testa o erro 400 quando ocorre um ValueError na atualização da tarefa.
    """
    mock_user = MagicMock()
    mock_user.id = "user_id_123"
    mock_get_user.return_value = mock_user

    existing_task = TaskResponse(
        id="task_id_123",
        user_id="user_id_123",
        title="Sample Task",
        description="Sample Description",
        deadline=datetime.datetime.now() + datetime.timedelta(days=1),
        priority="high",
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
        state="to_do",
    )
    mock_get_task_by_id.return_value = existing_task

    mock_update_task.side_effect = ValueError("Invalid task data")  # Simula erro de validação

    update_data = {"title": "Updated Task"}

    response = client.put("/tasks/task_id_123", json=update_data, headers={"Authorization": "Bearer valid_token"})
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Invalid task data"


@patch("routers.task.get_user")
@patch("routers.task.get_task_by_id")
@patch("routers.task.delete_task_by_id")  # Mock da função delete_task_by_id
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_delete_task_success(mock_jwt_bearer, mock_delete_task_by_id, mock_get_task_by_id, mock_get_user):
    """
    Testa a exclusão bem-sucedida de uma tarefa.
    """
    mock_user = MagicMock()
    mock_user.id = "user_id_123"
    mock_get_user.return_value = mock_user

    task_data = TaskResponse(
        id="task_id_123",
        user_id="user_id_123",
        title="Sample Task",
        description="Sample Description",
        deadline=datetime.datetime.now() + datetime.timedelta(days=1),
        priority="high",
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
        state=TaskState.TO_DO,
    )
    mock_get_task_by_id.return_value = task_data
    mock_delete_task_by_id.return_value = True

    response = client.delete("/tasks/task_id_123", headers={"Authorization": "Bearer valid_token"})

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""

@patch("routers.task.get_user")
@patch("routers.task.get_task_by_id")
@patch("routers.task.delete_task_by_id")
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_delete_task_not_found(mock_jwt_bearer, mock_delete_task_by_id, mock_get_task_by_id, mock_get_user):
    """
    Testa o erro 404 ao tentar excluir uma tarefa que não existe.
    """
    mock_user = MagicMock()
    mock_user.id = "user_id_123"
    mock_get_user.return_value = mock_user

    mock_get_task_by_id.side_effect = ValueError("Task not found.")

    response = client.delete("/tasks/non_existent_task_id", headers={"Authorization": "Bearer valid_token"})

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Task not found."

@patch("routers.task.get_user")
@patch("routers.task.get_task_by_id")
@patch("routers.task.delete_task_by_id")
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_delete_task_forbidden(mock_jwt_bearer, mock_delete_task_by_id, mock_get_task_by_id, mock_get_user):
    """
    Testa o erro 403 quando o usuário não tem permissão para excluir a tarefa.
    """
    mock_user = MagicMock()
    mock_user.id = "user_id_123"
    mock_get_user.return_value = mock_user

    task_data = TaskResponse(
        id="task_id_123",
        user_id="another_user_id",  # Diferente do usuário autenticado
        title="Sample Task",
        description="Sample Description",
        deadline=datetime.datetime.now() + datetime.timedelta(days=1),
        priority="high",
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
        state=TaskState.TO_DO,
    )
    mock_get_task_by_id.return_value = task_data

    response = client.delete("/tasks/task_id_123", headers={"Authorization": "Bearer valid_token"})

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "Not authorized to delete this task."

@patch("routers.task.get_user")
@patch("routers.task.get_tasks_by_user_id")
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_get_tasks_by_user(mock_jwt_bearer, mock_get_tasks_by_user_id, mock_get_user):
    """
    Testa a recuperação das tarefas do usuário autenticado com sucesso.
    """
    mock_user = MagicMock()
    mock_user.id = "user_id_123"
    mock_get_user.return_value = mock_user

    task_1 = TaskResponse(
        id="task_id_1",
        user_id="user_id_123",
        title="Task 1",
        description="First task",
        deadline=datetime.datetime.now() + datetime.timedelta(days=1),
        priority="medium",
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
        state=TaskState.TO_DO,
    )
    task_2 = TaskResponse(
        id="task_id_2",
        user_id="user_id_123",
        title="Task 2",
        description="Second task",
        deadline=datetime.datetime.now() + datetime.timedelta(days=2),
        priority="high",
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
        state=TaskState.IN_PROGRESS,
    )
    
    mock_get_tasks_by_user_id.return_value = [task_1, task_2]

    headers = {"Authorization": "Bearer valid_token"}
    response = client.get("/tasks", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["title"] == "Task 1"
    assert response.json()[1]["title"] == "Task 2"

@patch("routers.task.get_user")
@patch("routers.task.get_tasks_by_user_id")
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_get_tasks_by_user_no_tasks(mock_jwt_bearer, mock_get_tasks_by_user_id, mock_get_user):
    """
    Testa a recuperação quando o usuário não possui tarefas.
    """
    mock_user = MagicMock()
    mock_user.id = "user_id_123"
    mock_get_user.return_value = mock_user
    mock_get_tasks_by_user_id.return_value = []

    headers = {"Authorization": "Bearer valid_token"}
    response = client.get("/tasks", headers=headers)

    assert response.status_code == 200
    assert response.json() == []

@patch("routers.task.get_user")
@patch("routers.task.get_tasks_by_user_id")
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_get_tasks_by_user_not_found(mock_jwt_bearer, mock_get_tasks_by_user_id, mock_get_user):
    """
    Testa o erro 404 quando o usuário não é encontrado.
    """
    mock_get_user.return_value = None  # Simula usuário não encontrado

    headers = {"Authorization": "Bearer valid_token"}
    response = client.get("/tasks", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found."

@patch("routers.task.get_user")
@patch("routers.task.get_tasks_by_user_id")
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_get_tasks_by_user_unexpected_error(mock_jwt_bearer, mock_get_tasks_by_user_id, mock_get_user):
    """
    Testa o erro 500 quando ocorre uma exceção inesperada.
    """
    mock_user = MagicMock()
    mock_user.id = "user_id_123"
    mock_get_user.return_value = mock_user

    # Simula uma exceção inesperada no get_tasks_by_user_id
    mock_get_tasks_by_user_id.side_effect = Exception("Unexpected error")

    headers = {"Authorization": "Bearer valid_token"}
    response = client.get("/tasks", headers=headers)

    assert response.status_code == 500
    assert response.json()["detail"] == "An error occurred while retrieving tasks."