from vitae.modules.users.domain.entities import Profile, User
from vitae.modules.users.infra.persistence.models import ProfileModel, UserModel


def to_user(model: UserModel) -> User:
    return User(id=model.id, email=model.email, created_at=model.created_at)


def to_profile(model: ProfileModel) -> Profile:
    return Profile(
        user_id=model.user_id,
        display_name=model.display_name,
        date_of_birth=model.date_of_birth,
        sex=model.sex,
    )
