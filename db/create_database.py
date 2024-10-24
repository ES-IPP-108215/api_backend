from models.user import User

from db.database import engine


def create_tables():
    User.metadata.create_all(bind=engine)