from pydantic import BaseModel


class CreateUser(BaseModel):
    id: str
    given_name: str
    family_name: str
    username: str
    email: str