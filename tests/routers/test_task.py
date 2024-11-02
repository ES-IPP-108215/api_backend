import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import datetime
from main import app
from db.database import get_db
from routers.task import auth
from schemas.task import TaskResponse
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
        state="to_do",
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
    assert response.json()["state"] == "to_do"

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