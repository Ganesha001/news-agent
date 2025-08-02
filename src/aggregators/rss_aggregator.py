"""
RSS News Aggregator for fetching articles from configured RSS feeds.
"""

import asyncio
import aiohttp
import feedparser
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import hashlib
import re

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from ..utils.models import Article, NewsSource, ArticleCategory
from ..utils.config import config


class RSSAggregator:
    """Aggregates news articles from RSS feeds."""
    
    def __init__(self):
        """Initialize the RSS aggregator."""
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.max_concurrent = config.get("system.max_concurrent_requests", 10)
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def fetch_rss_feed(self, source: NewsSource) -> List[Article]:
        """Fetch articles from a single RSS feed.
        
        Args:
            source: News source configuration
            
        Returns:
            List of articles from the feed
        """
        async with self.semaphore:
            try:
                logger.info(f"Fetching RSS feed: {source.name} ({source.url})")
                
                if not self.session:
                    raise RuntimeError("Session not initialized. Use async context manager.")
                
                async with self.session.get(str(source.url)) as response:
                    if response.status != 200:
                        logger.error(f"Failed to fetch {source.name}: HTTP {response.status}")
                        return []
                    
                    content = await response.text()
                    feed = feedparser.parse(content)
                    
                    articles = []
                    for entry in feed.entries:
                        try:
                            article = await self._parse_entry(entry, source)
                            if article:
                                articles.append(article)
                        except Exception as e:
                            logger.error(f"Error parsing entry from {source.name}: {e}")
                            continue
                    
                    logger.info(f"Fetched {len(articles)} articles from {source.name}")
                    return articles
                    
            except Exception as e:
                logger.error(f"Error fetching RSS feed {source.name}: {e}")
                raise
    
    async def _parse_entry(self, entry: Dict[str, Any], source: NewsSource) -> Optional[Article]:
        """Parse a single RSS entry into an Article object.
        
        Args:
            entry: RSS entry dictionary
            source: News source configuration
            
        Returns:
            Article object or None if parsing fails
        """
        try:
            # Extract basic information
            title = entry.get('title', '').strip()
            if not title:
                return None
            
            # Generate unique ID
            article_id = self._generate_article_id(entry, source)
            
            # Parse publication date
            published_at = self._parse_date(entry.get('published', ''))
            if not published_at:
                published_at = datetime.now(timezone.utc)
            
            # Extract content
            content = self._extract_content(entry)
            description = entry.get('summary', '')
            
            # Extract author
            author = self._extract_author(entry)
            
            # Determine category
            category = self._determine_category(entry, source)
            
            # Extract keywords
            keywords = self._extract_keywords(entry, title, content)
            
            # Calculate word count
            word_count = len(content.split()) if content else 0
            reading_time = max(1, word_count // 200)  # Average reading speed
            
            article = Article(
                id=article_id,
                title=title,
                description=description,
                content=content,
                url=entry.get('link', ''),
                source=source,
                category=category,
                published_at=published_at,
                author=author,
                language=source.language,
                word_count=word_count,
                reading_time=reading_time,
                keywords=keywords,
                reliability_score=source.reliability_score,
                processed_at=datetime.now(timezone.utc)
            )
            
            return article
            
        except Exception as e:
            logger.error(f"Error parsing RSS entry: {e}")
            return None
    
    def _generate_article_id(self, entry: Dict[str, Any], source: NewsSource) -> str:
        """Generate a unique ID for an article.
        
        Args:
            entry: RSS entry dictionary
            source: News source configuration
            
        Returns:
            Unique article ID
        """
        # Use link as primary identifier, fallback to title + source
        link = entry.get('link', '')
        if link:
            return hashlib.md5(f"{link}".encode()).hexdigest()
        else:
            title = entry.get('title', '')
            return hashlib.md5(f"{title}_{source.name}".encode()).hexdigest()
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string from RSS feed.
        
        Args:
            date_str: Date string from RSS feed
            
        Returns:
            Parsed datetime or None if parsing fails
        """
        if not date_str:
            return None
        
        # Common RSS date formats
        date_formats = [
            '%a, %d %b %Y %H:%M:%S %z',  # RFC 822
            '%a, %d %b %Y %H:%M:%S %Z',  # RFC 822 with timezone name
            '%Y-%m-%dT%H:%M:%S%z',       # ISO 8601
            '%Y-%m-%dT%H:%M:%SZ',        # ISO 8601 UTC
            '%Y-%m-%d %H:%M:%S',         # Simple format
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
    
    def _extract_content(self, entry: Dict[str, Any]) -> str:
        """Extract article content from RSS entry.
        
        Args:
            entry: RSS entry dictionary
            
        Returns:
            Extracted content
        """
        # Try different content fields
        content_fields = ['content', 'summary', 'description']
        
        for field in content_fields:
            content = entry.get(field, '')
            if isinstance(content, list) and content:
                content = content[0].get('value', '')
            if content:
                return self._clean_html(content)
        
        return ""
    
    def _clean_html(self, html_content: str) -> str:
        """Clean HTML content and extract plain text.
        
        Args:
            html_content: HTML content string
            
        Returns:
            Cleaned plain text
        """
        # Simple HTML tag removal
        html_content = re.sub(r'<[^>]+>', '', html_content)
        # Remove extra whitespace
        html_content = re.sub(r'\s+', ' ', html_content)
        return html_content.strip()
    
    def _extract_author(self, entry: Dict[str, Any]) -> Optional[str]:
        """Extract author information from RSS entry.
        
        Args:
            entry: RSS entry dictionary
            
        Returns:
            Author name or None
        """
        author_fields = ['author', 'dc:creator', 'dc:author']
        
        for field in author_fields:
            author = entry.get(field, '')
            if author:
                return author.strip()
        
        return None
    
    def _determine_category(self, entry: Dict[str, Any], source: NewsSource) -> ArticleCategory:
        """Determine article category from entry and source.
        
        Args:
            entry: RSS entry dictionary
            source: News source configuration
            
        Returns:
            Article category
        """
        # Check entry category
        category = entry.get('category', '').lower()
        if category:
            category_mapping = {
                'politics': ArticleCategory.POLITICS,
                'technology': ArticleCategory.TECHNOLOGY,
                'business': ArticleCategory.BUSINESS,
                'health': ArticleCategory.HEALTH,
                'science': ArticleCategory.SCIENCE,
                'entertainment': ArticleCategory.ENTERTAINMENT,
                'sports': ArticleCategory.SPORTS,
            }
            
            for key, value in category_mapping.items():
                if key in category:
                    return value
        
        # Fallback to source category
        return source.category
    
    def _extract_keywords(self, entry: Dict[str, Any], title: str, content: str) -> List[str]:
        """Extract keywords from article entry.
        
        Args:
            entry: RSS entry dictionary
            title: Article title
            content: Article content
            
        Returns:
            List of keywords
        """
        keywords = []
        
        # Extract from tags
        tags = entry.get('tags', [])
        if isinstance(tags, list):
            for tag in tags:
                if isinstance(tag, dict):
                    keywords.append(tag.get('term', ''))
                else:
                    keywords.append(str(tag))
        
        # Extract from title (simple approach)
        title_words = re.findall(r'\b\w+\b', title.lower())
        # Filter out common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        title_keywords = [word for word in title_words if word not in stop_words and len(word) > 3]
        keywords.extend(title_keywords[:5])  # Limit to 5 keywords from title
        
        return list(set(keywords))  # Remove duplicates
    
    async def fetch_all_feeds(self) -> List[Article]:
        """Fetch articles from all configured RSS feeds.
        
        Returns:
            List of all articles from all feeds
        """
        sources = config.get_news_sources()
        if not sources:
            logger.warning("No news sources configured")
            return []
        
        # Convert to NewsSource objects
        news_sources = []
        for source_config in sources:
            try:
                source = NewsSource(**source_config)
                news_sources.append(source)
            except Exception as e:
                logger.error(f"Invalid source configuration: {e}")
                continue
        
        # Fetch all feeds concurrently
        tasks = [self.fetch_rss_feed(source) for source in news_sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine all articles
        all_articles = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error fetching from {news_sources[i].name}: {result}")
            elif isinstance(result, list):
                all_articles.extend(result)
        
        logger.info(f"Total articles fetched: {len(all_articles)}")
        return all_articles
    
    def filter_articles(self, articles: List[Article], 
                       min_reliability: float = 0.7,
                       max_age_hours: int = 24) -> List[Article]:
        """Filter articles based on criteria.
        
        Args:
            articles: List of articles to filter
            min_reliability: Minimum reliability score
            max_age_hours: Maximum age in hours
            
        Returns:
            Filtered list of articles
        """
        filtered = []
        cutoff_time = datetime.now(timezone.utc).replace(hour=datetime.now().hour - max_age_hours)
        
        for article in articles:
            # Check reliability
            if article.reliability_score < min_reliability:
                continue
            
            # Check age
            if article.published_at < cutoff_time:
                continue
            
            # Check for required fields
            if not article.title or not article.url:
                continue
            
            filtered.append(article)
        
        logger.info(f"Filtered {len(articles)} articles to {len(filtered)}")
        return filtered 