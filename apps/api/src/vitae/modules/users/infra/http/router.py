from typing import Annotated

from fastapi import APIRouter, Depends

from vitae.core.auth import CurrentUserId
from vitae.core.database import SessionDep
from vitae.core.errors import NotFoundError
from vitae.modules.users.application.service import UserService
from vitae.modules.users.infra.http.schemas import UserRead
from vitae.modules.users.infra.persistence.repository import PostgresUserRepository

router = APIRouter(prefix="/me", tags=["users"])


def get_user_service(session: SessionDep) -> UserService:
    return UserService(PostgresUserRepository(session))


ServiceDep = Annotated[UserService, Depends(get_user_service)]


@router.get("")
async def get_me(user_id: CurrentUserId, service: ServiceDep) -> UserRead:
    """Get the current user's account."""
    user = await service.get_user(user_id)
    if user is None:
        raise NotFoundError("user not found")
    return UserRead.model_validate(user)
