from vitae.modules.users.domain.entities import User
from vitae.modules.users.infra.persistence.models import UserModel


def to_user(model: UserModel) -> User:
    return User(id=model.id, email=model.email, created_at=model.created_at)
