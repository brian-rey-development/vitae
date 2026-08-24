from vitae.modules.profiles.domain.entities import Profile
from vitae.modules.profiles.infra.persistence.models import ProfileModel


def to_profile(model: ProfileModel) -> Profile:
    return Profile(
        user_id=model.user_id,
        display_name=model.display_name,
        date_of_birth=model.date_of_birth,
        sex=model.sex,
    )
