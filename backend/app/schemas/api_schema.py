from pydantic import BaseModel, Field


class HomeMeta(BaseModel):
    last_updated: str
    window_hours: int = 24
    total_events: int = 0


class StoryCard(BaseModel):
    id: int | None = None
    event_id: str
    headline: str
    summary: str
    why_it_matters: str
    region: str
    topic: str
    status: str
    importance_score: float
    published_at: str
    updated_at: str
    article_url: str | None = None
    source_list: list[str] = Field(default_factory=list)
    is_top_story: bool = False
    is_watchlist: bool = False


class HomeResponse(BaseModel):
    meta: HomeMeta
    top_stories: list[StoryCard] = Field(default_factory=list)
    by_region: dict[str, list[StoryCard]] = Field(default_factory=dict)
    by_topic: dict[str, list[StoryCard]] = Field(default_factory=dict)
    watchlist: list[StoryCard] = Field(default_factory=list)
