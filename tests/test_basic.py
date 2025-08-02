"""
Basic tests for the News Agent system.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch

from src.utils.models import Article, NewsSource, ArticleCategory
from src.utils.config import config


class TestModels:
    """Test data models."""
    
    def test_article_creation(self):
        """Test Article model creation."""
        source = NewsSource(
            name="Test Source",
            url="https://example.com/rss",
            reliability_score=0.9
        )
        
        article = Article(
            title="Test Article",
            url="https://example.com/article",
            source=source,
            category=ArticleCategory.GENERAL,
            published_at="2023-01-01T00:00:00Z"
        )
        
        assert article.title == "Test Article"
        assert article.source.name == "Test Source"
        assert article.category == ArticleCategory.GENERAL
    
    def test_news_source_creation(self):
        """Test NewsSource model creation."""
        source = NewsSource(
            name="BBC News",
            url="http://feeds.bbci.co.uk/news/rss.xml",
            category=ArticleCategory.GENERAL,
            reliability_score=0.93
        )
        
        assert source.name == "BBC News"
        assert source.reliability_score == 0.93
        assert source.is_active is True


class TestConfiguration:
    """Test configuration management."""
    
    def test_config_loading(self):
        """Test that configuration can be loaded."""
        # This test assumes config.yaml exists
        sources = config.get_news_sources()
        assert isinstance(sources, list)
    
    def test_config_get_method(self):
        """Test configuration get method."""
        # Test with default value
        value = config.get("nonexistent.key", "default")
        assert value == "default"
    
    def test_api_config(self):
        """Test API configuration retrieval."""
        openai_config = config.get_api_config("openai")
        assert isinstance(openai_config, dict)


@pytest.mark.asyncio
class TestAsyncComponents:
    """Test async components."""
    
    async def test_rss_aggregator_initialization(self):
        """Test RSS aggregator can be initialized."""
        from src.aggregators.rss_aggregator import RSSAggregator
        
        aggregator = RSSAggregator()
        assert aggregator is not None
        assert hasattr(aggregator, 'fetch_all_feeds')
    
    async def test_trend_analyzer_initialization(self):
        """Test trend analyzer can be initialized."""
        from src.trend_detection.trend_analyzer import TrendAnalyzer
        
        analyzer = TrendAnalyzer()
        assert analyzer is not None
        assert hasattr(analyzer, 'detect_trends')
    
    async def test_whatsapp_sender_initialization(self):
        """Test WhatsApp sender can be initialized."""
        from src.notification.whatsapp_sender import WhatsAppSender
        
        # Mock Twilio configuration to avoid actual API calls
        with patch('src.notification.whatsapp_sender.config') as mock_config:
            mock_config.get_api_config.return_value = {
                "account_sid": "test_sid",
                "auth_token": "test_token",
                "whatsapp_number": "whatsapp:+1234567890"
            }
            mock_config.get_notification_config.return_value = {
                "whatsapp": {
                    "enabled": True,
                    "max_messages_per_hour": 10
                }
            }
            
            sender = WhatsAppSender()
            assert sender is not None
            assert hasattr(sender, 'send_trend_notification')


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_article_filtering(self):
        """Test article filtering logic."""
        # Create test articles
        source = NewsSource(
            name="Test Source",
            url="https://example.com/rss",
            reliability_score=0.8
        )
        
        articles = [
            Article(
                title="Article 1",
                url="https://example.com/1",
                source=source,
                category=ArticleCategory.GENERAL,
                published_at="2023-01-01T00:00:00Z",
                reliability_score=0.9
            ),
            Article(
                title="Article 2",
                url="https://example.com/2",
                source=source,
                category=ArticleCategory.GENERAL,
                published_at="2023-01-01T00:00:00Z",
                reliability_score=0.3  # Low reliability
            )
        ]
        
        # Test filtering by reliability
        from src.aggregators.rss_aggregator import RSSAggregator
        aggregator = RSSAggregator()
        
        filtered = aggregator.filter_articles(articles, min_reliability=0.5)
        assert len(filtered) == 1
        assert filtered[0].title == "Article 1"


if __name__ == "__main__":
    pytest.main([__file__]) 