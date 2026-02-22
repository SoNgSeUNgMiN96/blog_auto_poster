from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ImageInput(BaseModel):
    url: str
    type: str = "general"


class GeneratePostRequest(BaseModel):
    content_type: str
    prompt_template: str
    prompt_variables: dict[str, Any] = Field(default_factory=dict)
    images: list[ImageInput] = Field(default_factory=list)
    render_template: str = "ott_review.html"
    system_role: str | None = None
    auto_publish: bool = False

    model_config = ConfigDict(extra="allow")
