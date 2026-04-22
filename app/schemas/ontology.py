from pydantic import BaseModel, ConfigDict, Field


class StyleCreate(BaseModel):
    key: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=255)
    level: int = Field(default=1, ge=1)
    parent_id: int | None = None


class StyleUpdate(StyleCreate):
    pass


class StyleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    label: str
    level: int
    parent_id: int | None


class EmotionCreate(BaseModel):
    category_id: int
    key: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=255)


class EmotionUpdate(EmotionCreate):
    pass


class EmotionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    key: str
    label: str


class InfluenceCreate(BaseModel):
    category_id: int
    key: str = Field(min_length=1, max_length=160)
    label: str = Field(min_length=1, max_length=255)


class InfluenceUpdate(InfluenceCreate):
    pass


class InfluenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    key: str
    label: str


class GeographyCreate(BaseModel):
    key: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=255)
    description: str | None = None


class GeographyUpdate(GeographyCreate):
    pass


class GeographyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    label: str
    description: str | None
