import pytest
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.mysql import MySqlContainer

from db.database import get_db
from main import app
from models.user import User as UserModel
from schemas.user import CreateUser
from crud.user import create_user, get_user_by_username, get_user_by_email, get_user, get_user_by_id
from fastapi import HTTPException


# Configuração de logging para facilitar a depuração
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuração do container MySQL para testes
my_sql_container = MySqlContainer(
    "mysql:8.0",
    root_password="test_root_password",
    dbname="test_db",
    username="test_username",
    password="test_password",
)


@pytest.fixture(name="session", scope="module")
def setup():
    """
    Fixture to setup the MySQL container and create a session for the tests.
    """
    # Inicia o container MySQL
    my_sql_container.start()
    connection_url = my_sql_container.get_connection_url()
    engine = create_engine(connection_url, connect_args={})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    UserModel.metadata.create_all(engine)  

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield SessionLocal 
    my_sql_container.stop()


@pytest.fixture(name="test_db", scope="module")
def create_test_db(session):
    """
    Fixture to create a test database session.
    """
    db = session()  
    yield db
    db.close() 


@pytest.fixture(name="test_user", scope="function")
def create_test_user(test_db):
    """
    Fixture to create a test user in the database.
    """
    test_user = UserModel(
        id="id1",
        given_name="given_name1",
        family_name="family_name1",
        username="username1",
        email="email1",
    )
    test_db.add(test_user)
    test_db.commit() 
    yield test_user
    test_db.delete(test_user)  
    test_db.commit()  


def test_create_user(test_db):
    """
    Test the creation of a user in the database.
    """
    user_data = CreateUser(
        id="id2",
        given_name="given_name2",
        family_name="family_name2",
        username="username2",
        email="email2",
    )
    created_user = create_user(
        user_data, test_db
    )  

    assert created_user is not None
    assert created_user.username == "username2"
    assert created_user.email == "email2"
    assert created_user.given_name == "given_name2"
    assert created_user.family_name == "family_name2"

def test_get_user_found(test_db, test_user):
    """
    Testa a função get_user quando o usuário é encontrado.
    """
    found_user = get_user(test_user.username, test_db)
    assert found_user is not None
    assert found_user.username == test_user.username
    assert found_user.email == test_user.email
    assert found_user.given_name == test_user.given_name
    assert found_user.family_name == test_user.family_name

def test_get_user_not_found(test_db):
    """
    Testa a função get_user quando o usuário não é encontrado.
    """
    with pytest.raises(HTTPException) as exc_info:
        get_user("username_not_exist", test_db)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "User not found"


def test_get_user_by_username_found(test_db, test_user):
    """
    Test the search for a user using a username that exists in the database.
    """
    found_user = get_user_by_username(test_user.username, test_db) 

    assert found_user is not None
    assert found_user.id == test_user.id


def test_get_user_by_username_not_found(test_db):
    """
    Test the search for a user using a username that does not exist in the database.
    """
    found_user = get_user_by_username(
        "not_exist", test_db
    )  
    assert found_user is None 


def test_get_user_by_email_found(test_db, test_user):
    """
    Test the search for a user using an email that exists in the database.
    """
    found_user = get_user_by_email(test_user.email, test_db)

    assert found_user is not None
    assert found_user.id == test_user.id


def test_get_user_by_email_not_found(test_db):
    """
    Test the search for a user using an email that does not exist in the database.
    """
    found_user = get_user_by_email(
        "not_exist@email.com", test_db
    ) 
    assert found_user is None  

def test_get_user_by_id_found(test_db, test_user):
    """
    Test the search for a user using an ID that exists in the database.
    """
    found_user = get_user_by_id(test_user.id, test_db)

    assert found_user is not None
    assert found_user.username == test_user.username
    assert found_user.email == test_user.email
    assert found_user.given_name == test_user.given_name
    assert found_user.family_name == test_user.family_name

def test_get_user_by_id_not_found(test_db):
    """
    Test the search for a user using an ID that does not exist in the database.
    """
    found_user = get_user_by_id(
        9999, test_db
    )
    assert found_user is None