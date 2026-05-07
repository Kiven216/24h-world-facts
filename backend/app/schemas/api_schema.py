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
    signal_tags: list[str] = Field(default_factory=list)
    is_top_story: bool = False
    is_watchlist: bool = False


class HomeDebugSummary(BaseModel):
    selection_generated_at: str = ""
    candidate_count: int = 0
    source_counts: dict[str, int] = Field(default_factory=dict)
    selected_source_counts: dict[str, int] = Field(default_factory=dict)
    selected_top_count: int = 0
    suppressed_count: int = 0
    final_suppressed_count: int = 0
    selected_after_fallback_count: int = 0
    strong_selected_after_fallback_count: int = 0
    moderate_selected_after_fallback_count: int = 0
    strong_same_event_count: int = 0
    moderate_same_event_count: int = 0
    suppressed_by_bucket: dict[str, int] = Field(default_factory=dict)


class HomeDebugSelectedStory(BaseModel):
    event_id: str
    source: str
    headline: str
    topic: str
    score: float
    event_key: str = ""
    anchors: list[str] = Field(default_factory=list)


class HomeDebugSuppressedCandidate(BaseModel):
    bucket: str
    candidate: HomeDebugSelectedStory
    matched_reference: HomeDebugSelectedStory
    reason: str
    same_event_strength: str
    match_class: str = ""
    match_rule: str = ""
    action: str = ""
    shared_anchors: list[str] = Field(default_factory=list)
    event_key: str = ""


class HomeDebugPayload(BaseModel):
    summary: HomeDebugSummary
    selected_top_stories: list[HomeDebugSelectedStory] = Field(default_factory=list)
    suppressed: list[HomeDebugSuppressedCandidate] = Field(default_factory=list)


class HomeResponse(BaseModel):
    meta: HomeMeta
    top_stories: list[StoryCard] = Field(default_factory=list)
    by_region: dict[str, list[StoryCard]] = Field(default_factory=dict)
    by_topic: dict[str, list[StoryCard]] = Field(default_factory=dict)
    watchlist: list[StoryCard] = Field(default_factory=list)
    debug: HomeDebugPayload | None = None
