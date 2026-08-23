import uuid
from typing import Annotated

from fastapi import Depends

from vitae.core.settings import get_settings

DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def get_current_user_id() -> uuid.UUID:
    if get_settings().is_production:
        raise RuntimeError("dev auth stub is not allowed in production; real auth lands in M18")
    return DEV_USER_ID


CurrentUserId = Annotated[uuid.UUID, Depends(get_current_user_id)]
