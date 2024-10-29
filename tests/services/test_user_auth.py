import base64
import os
import pytest
import logging
from unittest.mock import patch
from auth.user_auth import auth_with_code, user_info_with_token, logout_with_token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

cognito_user_client_id = "client_id"
cognito_user_client_secret = "client_secret"
cognito_token_endpoint = "http://token_endpoint"
headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Authorization": f"Basic {base64.b64encode(f'{cognito_user_client_id}:{cognito_user_client_secret}'.encode()).decode()}",
}


class RequestsMockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code
        self.text = "error reason"

    def json(self):
        return self.json_data


@pytest.fixture(autouse=True, scope="module")
def setup_environ():
    logger.info("Setting up environment")
    os.environ["COGNITO_USER_CLIENT_ID"] = cognito_user_client_id
    os.environ["COGNITO_USER_CLIENT_SECRET"] = cognito_user_client_secret
    os.environ["COGNITO_TOKEN_ENDPOINT"] = cognito_token_endpoint


# 400 it's just a random error status code to test the error handling
@patch("auth.user_auth.requests.post", return_value=RequestsMockResponse({}, 400))
def test_unsuccessful_auth_with_code(requests_post_mock):
    payload = {
        "grant_type": "authorization_code",
        "code": "code",
        "client_id": cognito_user_client_id,
        "redirect_uri": "redirect_uri",
    }

    result = auth_with_code("code", "redirect_uri")

    requests_post_mock.assert_called_once_with(
        cognito_token_endpoint, data=payload, headers=headers
    )
    assert result is None


@patch(
    "auth.user_auth.requests.post",
    return_value=RequestsMockResponse(
        {"access_token": "client_access_token", "expires_in": 200}, 200
    ),
)
def test_successful_auth_with_code(requests_post_mock):
    payload = {
        "grant_type": "authorization_code",
        "code": "code",
        "client_id": cognito_user_client_id,
        "redirect_uri": "redirect_uri",
    }

    result = auth_with_code("code", "redirect_uri")

    requests_post_mock.assert_called_once_with(
        cognito_token_endpoint, data=payload, headers=headers
    )
    assert result == {"token": "client_access_token", "expires_in": 200}


@patch(
    "auth.user_auth.cognito_client.get_user",
    return_value={"ResponseMetadata": {"HTTPStatusCode": 200}},
)
def test_user_info_with_token(mock_cognito_client_get_user_function):
    result = user_info_with_token("access_token")

    mock_cognito_client_get_user_function.assert_called_once_with(
        AccessToken="access_token"
    )
    assert result == {"ResponseMetadata": {"HTTPStatusCode": 200}}


# 400 it's just a random error status code to test the error handling
@patch(
    "auth.user_auth.cognito_client.get_user",
    return_value={"ResponseMetadata": {"HTTPStatusCode": 400}},
)
def test_unsuccessful_user_info_with_token(mock_cognito_client_get_user_function):
    result = user_info_with_token("access_token_2")

    mock_cognito_client_get_user_function.assert_called_once_with(
        AccessToken="access_token_2"
    )
    assert result is None


@patch(
    "auth.user_auth.cognito_client.global_sign_out",
    return_value={"ResponseMetadata": {"HTTPStatusCode": 200}},
)
def test_logout_with_token(mock_cognito_client_global_sign_out_function):
    result = logout_with_token("access_token")

    mock_cognito_client_global_sign_out_function.assert_called_once_with(
        AccessToken="access_token"
    )
    assert result == True


# 400 it's just a random error status code to test the error handling
@patch(
    "auth.user_auth.cognito_client.global_sign_out",
    return_value={"ResponseMetadata": {"HTTPStatusCode": 400}},
)
def test_unsuccessful_logout_with_token(mock_cognito_client_global_sign_out_function):
    result = logout_with_token("access_token_2")

    mock_cognito_client_global_sign_out_function.assert_called_once_with(
        AccessToken="access_token_2"
    )
    assert result == False

@patch(
    "auth.user_auth.cognito_client.global_sign_out",
    side_effect=Exception("Unexpected error occurred"),
)
def test_exception_during_logout(mock_cognito_client_global_sign_out_function):
    """
    Testa se a função lida corretamente com exceções inesperadas durante o logout.
    """

    # Executa a função que deve gerar uma exceção
    result = logout_with_token("access_token_with_error")

    # Verifica se o método global_sign_out foi chamado
    mock_cognito_client_global_sign_out_function.assert_called_once_with(
        AccessToken="access_token_with_error"
    )

    # Como ocorreu uma exceção, o resultado esperado é False
    assert result is False