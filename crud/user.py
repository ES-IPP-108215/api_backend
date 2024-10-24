from fastapi import HTTPException

from fastapi import Depends
from sqlalchemy.orm import Session

from db.database import get_db
from models.user import User as UserModel
from schemas.user import CreateUser

def create_user(new_user: CreateUser, db: Session = Depends(get_db)):
    """
    Save a new user in the database.

    :param new_user: User object to save.
    :param db: Database session.
    :return: User object saved.
    """
    db_user = UserModel(
        id=new_user.id,
        given_name=new_user.given_name,
        family_name=new_user.family_name,
        username=new_user.username,
        email=new_user.email,
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user

def new_user(user: CreateUser, db: Session = Depends(get_db)):
    """
    Create a new user in the database.

    :param user: User object to create.
    :param db: Database session.
    :return: User object created.
    """
    return save_user(new_user=user, db=db)


def get_user_by_username(username: str, db: Session = Depends(get_db)):
    """
    Get a user by username.

    :param username: Username of the user to get.
    :param db: Database session.
    :return: User object if found, otherwise None.
    """

    return db.query(UserModel).filter(UserModel.username == username).first()

def get_user_by_email(email: str, db: Session = Depends(get_db)):
    """
    Get a user by email.

    :param email: Email of the user to get.
    :param db: Database session.
    :return: User object if found, otherwise None.
    """

    return db.query(UserModel).filter(UserModel.email == email).first()

def get_user(username: str, db: Session = Depends(get_db)):
    """
    Get a user by username.

    :param username: Username of the user to get.
    :param db: Database session.
    :return: User object if found, otherwise raise an HTTPException.
    """
    db_user = get_user_by_username(username, db)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user