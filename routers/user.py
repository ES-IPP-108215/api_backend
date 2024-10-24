import os
import logging
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse
from pydantic import BaseModel, Field

from db.database import get_db
from auth.auth import jwks, get_current_user
from auth.JWTBearer import JWTBearer
from auth.user_auth import auth_with_code, user_info_with_token
from crud.user import create_user, get_user_by_username, get_user_by_email
from schemas.user import CreateUser

# Load environment variables
load_dotenv()

# Router and Auth setup
router = APIRouter(tags=["Authentication and Authorization"])
auth = JWTBearer(jwks)
COGNITO_REDIRECT_URI = os.getenv("REDIRECT_URI")


# Request model
class SignInRequest(BaseModel):
    code: str = Field(..., description="Authorization code obtained after user login.")


@router.post("/auth/signin", response_model=dict, status_code=status.HTTP_200_OK)
async def signin(request: SignInRequest, db: Session = Depends(get_db)):
    """
    Endpoint to log in a user and return an access token.
    """
    try:
        # Authenticate and retrieve token
        token = auth_with_code(request.code, COGNITO_REDIRECT_URI)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization code.",
            )

        # Retrieve user info from token
        user_info = user_info_with_token(token.get("token"))
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to retrieve user information.",
            )

        # Extract user attributes
        user_attributes = {attr["Name"]: attr["Value"] for attr in user_info["UserAttributes"]}

        new_user = CreateUser(
            id=user_attributes.get("sub"),
            given_name=user_attributes.get("given_name"),
            family_name=user_attributes.get("family_name"),
            username=user_info["Username"],
            email=user_attributes.get("email"),
        )

        # Check for existing user and create if not exists
        if not (existing_user := get_user_by_username(new_user.username, db) or get_user_by_email(new_user.email, db)):
            create_user(new_user, db)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"token": token, "message": "Login successful."},
        )

    except HTTPException as http_exc:
        raise http_exc
    except Exception:
        logging.exception("Unexpected error during sign-in.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during sign-in.",
        )


@router.get("/auth/me", dependencies=[Depends(auth)], response_model=dict, status_code=status.HTTP_200_OK)
async def get_current_user_info(
    current_username: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the authenticated user's information.
    """
    print(current_username)

    try:
        # Retrieve user by username
        user = get_user_by_username(current_username, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )
        return JSONResponse(status_code=status.HTTP_200_OK, content=jsonable_encoder(user))

    except HTTPException as http_exc:
        raise http_exc
    except Exception:
        logging.exception(f"Error retrieving user info for '{current_username}'.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving user information.",
        )
