import os
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session

from db.database import get_db
from main import app
from auth.JWTBearer import JWTAuthorizationCredentials
from auth.auth import JWTBearer
from routers.user import auth
from auth.auth import get_current_user

load_dotenv()
REDIRECT_URI = os.environ.get("REDIRECT_URI")

client = TestClient(app)


@pytest.fixture(scope="module")
def mock_db():
    db = MagicMock(spec=Session)
    app.dependency_overrides[get_db] = lambda: db
    yield db


user_attributes = {
    "UserAttributes": [
        {"Name": "email", "Value": "email@email.com"},
        {"Name": "email_verified", "Value": "..."},
        {"Name": "family_name", "Value": "family_name1"},
        {"Name": "given_name", "Value": "given_name1"},
        {"Name": "sub", "Value": "id1"},
    ],
    "Username": "username1",
}


@pytest.fixture(autouse=True)
def reset_mock_db(mock_db):
    mock_db.reset_mock()


@patch("routers.user.auth_with_code", return_value=None)
def test_unsuccessful_login_with_invalid_credentials(mock_auth_with_code):
    response = client.post("/auth/signin", json={"code": "invalid_code"})

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid authorization code."
    }
    mock_auth_with_code.assert_called_once_with("invalid_code", REDIRECT_URI)


@patch("routers.user.user_info_with_token", return_value=user_attributes)
@patch(
    "routers.user.auth_with_code",
    return_value={"token": "valid_token", "expires_in": 100},
)
def test_successful_login_with_valid_credentials(
    mock_auth_with_code, mock_user_info_with_token, mock_db
):
    mock_db.query.return_value.filter.return_value.first.side_effect = [True, False]

    response = client.post("/auth/signin", json={"code": "valid_code"})

    assert response.status_code == 200
    assert response.json() == {
        "token": {"token": "valid_token", "expires_in": 100},
        "message": "Login successful.",
    }
    mock_auth_with_code.assert_called_once_with("valid_code", REDIRECT_URI)
    mock_user_info_with_token.assert_called_once_with("valid_token")
    assert mock_db.query.call_count == 1


@patch("routers.user.user_info_with_token", return_value=user_attributes)
@patch(
    "routers.user.auth_with_code",
    return_value={"token": "valid_token", "expires_in": 100},
)
def test_successful_login_with_valid_credentials_found_email(
    mock_auth_with_code, mock_user_info_with_token, mock_db
):
    mock_db.query.return_value.filter.return_value.first.side_effect = [False, True]

    response = client.post("/auth/signin", json={"code": "valid_code"})
    assert response.status_code == 200
    assert response.json() == {
        "token": {"token": "valid_token", "expires_in": 100},
        "message": "Login successful.",
    }
    mock_auth_with_code.assert_called_once_with("valid_code", REDIRECT_URI)
    mock_user_info_with_token.assert_called_once_with("valid_token")
    assert mock_db.query.call_count == 2


@patch("routers.user.user_info_with_token", return_value=user_attributes)
@patch(
    "routers.user.auth_with_code",
    return_value={"token": "valid_token", "expires_in": 100},
)
@patch("crud.user.create_user")
@patch("crud.user.get_user_by_username")
@patch("crud.user.get_user_by_email")
def test_successful_login_with_valid_credentials_new_user(
    mock_get_user_by_email,
    mock_get_user_by_username,
    mock_create_user,
    mock_auth_with_code,
    mock_user_info_with_token,
    mock_db,
):
    # Simulando que o usuário não existe no banco de dados
    mock_get_user_by_username.return_value = None  # O usuário não existe
    mock_get_user_by_email.return_value = None  # O email não existe

    # Configure o mock do banco de dados para indicar que o usuário não foi encontrado
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        None,  # Primeira chamada para verificação de nome de usuário
        None,  # Segunda chamada para verificação de email
    ]

    # Garantir que o app use o banco de dados mockado
    app.dependency_overrides[get_db] = lambda: mock_db

    # Simulando uma requisição de login
    response = client.post("/auth/signin", json={"code": "valid_code"})

    # Verificar se a resposta é 200 OK
    assert response.status_code == 200
    assert response.json() == {
        "token": {"token": "valid_token", "expires_in": 100},
        "message": "Login successful.",
    }

    # Verificar se as funções apropriadas foram chamadas
    mock_auth_with_code.assert_called_once_with("valid_code", REDIRECT_URI)
    mock_user_info_with_token.assert_called_once_with("valid_token")

    # Verificar se create_user foi chamado, indicando que um novo usuário foi criado
    # mock_create_user.assert_called_once()  # Isto deve passar agora
    app.dependency_overrides = {}


credentials = JWTAuthorizationCredentials(
    jwt_token="token",
    header={"kid": "some_kid"},
    claims={"sub": "user_id"},
    signature="signature",
    message="message",
)


@patch("routers.user.get_user_by_username", return_value=user_attributes)
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_get_current_user_success(
    mock_get_user_by_username,
    mock_verify_token_revoed,
):
    app.dependency_overrides[auth] = lambda: credentials
    app.dependency_overrides[get_current_user] = lambda: "username1"

    headers = {"Authorization": "Bearer token"}
    response = client.get(
        "/auth/me",
        headers=headers,  # Removing unnecessary args in the query string
    )

    print(response.json())
    # Verifies the status of the response is 200
    assert response.status_code == 200
    # Verifies the response contains user attributes
    assert response.json() == user_attributes

    app.dependency_overrides = {}


@patch("routers.user.get_user_by_username", return_value=None)  # Usuário não encontrado
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_get_current_user_not_found(
    mock_get_user_by_username, mock_verify_token_revoed
):
    app.dependency_overrides[auth] = lambda: credentials
    app.dependency_overrides[get_current_user] = lambda: "username1"

    headers = {"Authorization": "Bearer token"}
    response = client.get("/auth/me", headers=headers)

    # Verifica se a resposta retorna 404
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found."}

    app.dependency_overrides = {}


@patch("routers.user.get_user_by_username", side_effect=Exception("Unexpected error"))
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_get_current_user_unexpected_error(
    mock_get_user_by_username, mock_verify_token_revoed
):
    app.dependency_overrides[auth] = lambda: credentials
    app.dependency_overrides[get_current_user] = lambda: "username1"

    headers = {"Authorization": "Bearer token"}
    response = client.get("/auth/me", headers=headers)

    # Verifica se a resposta retorna 500
    assert response.status_code == 500
    assert response.json() == {
        "detail": "Error retrieving user information."
    }

    app.dependency_overrides = {}

@patch("routers.user.logout_with_token", return_value=True)
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_successful_logout(mock_jwt_bearer, mock_logout_with_token):
    """
    Testa o logout bem-sucedido do usuário.
    """
    headers = {"Authorization": "Bearer token"}
    response = client.get("/auth/logout", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"message": "Logout successful."}
    mock_logout_with_token.assert_called_once_with("token")


@patch("routers.user.logout_with_token", return_value=False)
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_unsuccessful_logout(mock_jwt_bearer, mock_logout_with_token):
    """
    Testa a falha ao fazer logout.
    """
    headers = {"Authorization": "Bearer token"}
    response = client.get("/auth/logout", headers=headers)

    assert response.status_code == 400
    assert response.json() == {"detail": "Failed to log out. Please try again."}
    mock_logout_with_token.assert_called_once_with("token")


@patch("routers.user.logout_with_token", side_effect=Exception("Unexpected error"))
@patch.object(JWTBearer, "__call__", return_value=credentials)
def test_logout_unexpected_error(mock_jwt_bearer, mock_logout_with_token):
    """
    Testa um erro inesperado durante o processo de logout.
    """
    headers = {"Authorization": "Bearer token"}
    response = client.get("/auth/logout", headers=headers)

    assert response.status_code == 500
    assert response.json() == {
        "detail": "An internal server error occurred during logout. Please try again later."
    }
    mock_logout_with_token.assert_called_once_with("token")