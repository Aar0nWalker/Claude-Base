from datetime import datetime
from pydantic import BaseModel


class SystemPromptOut(BaseModel):
    key: str
    label: str
    content: str
    updated_at: datetime

    model_config = {"from_attributes": True}


class SystemPromptUpdate(BaseModel):
    content: str


class AppSettingOut(BaseModel):
    key: str
    value: str

    model_config = {"from_attributes": True}


class AppSettingUpdate(BaseModel):
    value: str
