"""
Data models for the News Agent system.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl


class SourceReliability(str, Enum):
    """Reliability levels for news sources."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ArticleCategory(str, Enum):
    """Categories for news articles."""
    POLITICS = "politics"
    TECHNOLOGY = "technology"
    BUSINESS = "business"
    HEALTH = "health"
    SCIENCE = "science"
    ENTERTAINMENT = "entertainment"
    SPORTS = "sports"
    GENERAL = "general"


class NotificationType(str, Enum):
    """Types of notifications."""
    INSTANT_ALERT = "instant_alert"
    MORNING_BRIEFING = "morning_briefing"
    EVENING_SUMMARY = "evening_summary"
    TREND_UPDATE = "trend_update"


class NewsSource(BaseModel):
    """Model for news sources."""
    name: str
    url: HttpUrl
    category: ArticleCategory = ArticleCategory.GENERAL
    reliability_score: float = Field(ge=0.0, le=1.0)
    language: str = "en"
    is_active: bool = True
    last_updated: Optional[datetime] = None


class Article(BaseModel):
    """Model for news articles."""
    id: Optional[str] = None
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    url: HttpUrl
    source: NewsSource
    category: ArticleCategory
    published_at: datetime
    author: Optional[str] = None
    language: str = "en"
    
    # Metadata
    word_count: Optional[int] = None
    reading_time: Optional[int] = None
    keywords: List[str] = Field(default_factory=list)
    
    # Validation and quality metrics
    reliability_score: float = Field(ge=0.0, le=1.0)
    fact_check_score: Optional[float] = Field(ge=0.0, le=1.0)
    cross_reference_count: int = 0
    
    # Processing metadata
    processed_at: Optional[datetime] = None
    summary: Optional[str] = None
    sentiment_score: Optional[float] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Trend(BaseModel):
    """Model for trending news stories."""
    id: Optional[str] = None
    title: str
    description: str
    keywords: List[str]
    articles: List[Article]
    category: ArticleCategory
    
    # Trend metrics
    article_count: int
    source_count: int
    trend_score: float = Field(ge=0.0, le=1.0)
    confidence_score: float = Field(ge=0.0, le=1.0)
    
    # Temporal data
    first_seen: datetime
    last_updated: datetime
    duration_hours: Optional[int] = None
    
    # Summary and analysis
    summary: Optional[str] = None
    key_facts: List[str] = Field(default_factory=list)
    source_links: List[HttpUrl] = Field(default_factory=list)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Notification(BaseModel):
    """Model for notifications."""
    id: Optional[str] = None
    type: NotificationType
    recipient: str
    content: str
    title: Optional[str] = None
    
    # Associated data
    trend_id: Optional[str] = None
    article_ids: List[str] = Field(default_factory=list)
    
    # Delivery metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = None
    delivered: bool = False
    delivery_status: Optional[str] = None
    
    # Formatting
    format: str = "markdown"
    priority: str = "normal"  # low, normal, high, urgent
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UserPreferences(BaseModel):
    """Model for user preferences."""
    user_id: str
    topics_of_interest: List[ArticleCategory] = Field(default_factory=list)
    notification_frequency: str = "instant"  # instant, hourly, daily
    language: str = "en"
    timezone: str = "UTC"
    
    # Notification settings
    whatsapp_enabled: bool = True
    email_enabled: bool = False
    push_enabled: bool = False
    
    # Content preferences
    max_articles_per_notification: int = 5
    include_source_links: bool = True
    include_summaries: bool = True
    
    # Filtering
    blocked_keywords: List[str] = Field(default_factory=list)
    blocked_sources: List[str] = Field(default_factory=list)
    min_reliability_score: float = 0.7
    
    # Scheduling
    morning_briefing_time: str = "08:00"
    evening_summary_time: str = "20:00"
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "07:00"


class SystemMetrics(BaseModel):
    """Model for system performance metrics."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Performance metrics
    articles_processed: int = 0
    trends_detected: int = 0
    notifications_sent: int = 0
    api_requests: int = 0
    errors_count: int = 0
    
    # Response times
    avg_processing_time: float = 0.0
    avg_api_response_time: float = 0.0
    
    # System health
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    disk_usage: float = 0.0
    
    # Cache metrics
    cache_hit_rate: float = 0.0
    cache_size: int = 0
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class APIResponse(BaseModel):
    """Standard API response model."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        } 