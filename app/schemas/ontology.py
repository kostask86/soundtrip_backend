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


class EmotionCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    label: str


class EmotionCategoryWithChildren(EmotionCategoryRead):
    children: list[EmotionRead]


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


class InfluenceCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    label: str


class InfluenceCategoryWithChildren(InfluenceCategoryRead):
    children: list[InfluenceRead]


class TimePeriodCreate(BaseModel):
    key: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=255)
    description: str | None = None


class TimePeriodUpdate(TimePeriodCreate):
    pass


class TimePeriodRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    label: str
    description: str | None


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
