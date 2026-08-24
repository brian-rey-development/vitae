from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field, field_validator

from vitae.modules.users.domain.constants import DISPLAY_NAME_MAX_LENGTH
from vitae.modules.users.domain.enums import Sex


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=DISPLAY_NAME_MAX_LENGTH)
    date_of_birth: date | None = None
    sex: Sex | None = None

    @field_validator("date_of_birth")
    @classmethod
    def not_in_future(cls, value: date | None) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("date_of_birth cannot be in the future")
        return value


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    display_name: str | None
    date_of_birth: date | None
    sex: Sex | None

    @computed_field
    @property
    def age(self) -> int | None:
        if self.date_of_birth is None:
            return None
        today = date.today()
        birthday = (self.date_of_birth.month, self.date_of_birth.day)
        had_birthday = (today.month, today.day) >= birthday
        return today.year - self.date_of_birth.year - (0 if had_birthday else 1)


class MeRead(BaseModel):
    email: EmailStr
    profile: ProfileRead | None
