"""
Main News Agent Orchestrator - Coordinates all components for automated news processing.
"""

import asyncio
import signal
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import time

from loguru import logger
import sentry_sdk

from .aggregators.rss_aggregator import RSSAggregator
from .trend_detection.trend_analyzer import TrendAnalyzer
from .summarization.summarizer import NewsSummarizer
from .validation.fact_checker import FactChecker
from .notification.whatsapp_sender import WhatsAppSender
from .utils.models import Article, Trend, NotificationType, SystemMetrics
from .utils.config import config


class NewsAgent:
    """Main orchestrator for the automated news agent system."""
    
    def __init__(self):
        """Initialize the news agent."""
        self.running = False
        self.last_run = None
        self.metrics = SystemMetrics()
        
        # Initialize components
        self.aggregator = RSSAggregator()
        self.trend_analyzer = TrendAnalyzer()
        self.summarizer = NewsSummarizer()
        self.fact_checker = FactChecker()
        self.whatsapp_sender = WhatsAppSender()
        
        # Configuration
        self.user_preferences = config.get_user_preferences()
        self.notification_config = config.get_notification_config()
        self.system_config = config.get_system_config()
        
        # State tracking
        self.processed_articles = []
        self.detected_trends = []
        self.sent_notifications = []
        
        # Setup logging
        self._setup_logging()
        
        # Setup monitoring
        self._setup_monitoring()
        
        logger.info("News Agent initialized successfully")
    
    def _setup_logging(self):
        """Setup logging configuration."""
        log_level = self.system_config.get("log_level", "INFO")
        logger.remove()  # Remove default handler
        logger.add(
            sys.stdout,
            level=log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        )
        logger.add(
            "logs/news_agent.log",
            rotation="1 day",
            retention="30 days",
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
        )
    
    def _setup_monitoring(self):
        """Setup monitoring and error tracking."""
        sentry_dsn = self.system_config.get("monitoring", {}).get("sentry_dsn")
        if sentry_dsn:
            sentry_sdk.init(dsn=sentry_dsn)
            logger.info("Sentry monitoring initialized")
    
    async def start(self):
        """Start the news agent."""
        if self.running:
            logger.warning("News Agent is already running")
            return
        
        self.running = True
        logger.info("Starting News Agent...")
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        try:
            # Main processing loop
            while self.running:
                start_time = time.time()
                
                try:
                    await self._process_news_cycle()
                    self.last_run = datetime.now()
                    
                    # Update metrics
                    self._update_metrics(start_time)
                    
                    # Wait for next cycle
                    await self._wait_for_next_cycle()
                    
                except Exception as e:
                    logger.error(f"Error in news processing cycle: {e}")
                    await self._handle_error(e)
                    await asyncio.sleep(60)  # Wait before retrying
                    
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the news agent."""
        logger.info("Stopping News Agent...")
        self.running = False
        
        # Cleanup
        await self._cleanup()
        logger.info("News Agent stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}")
        asyncio.create_task(self.stop())
    
    async def _process_news_cycle(self):
        """Process a complete news cycle."""
        logger.info("Starting news processing cycle")
        
        # 1. Fetch news articles
        articles = await self._fetch_articles()
        if not articles:
            logger.warning("No articles fetched")
            return
        
        # 2. Detect trends
        trends = await self._detect_trends(articles)
        if not trends:
            logger.info("No trends detected")
            return
        
        # 3. Validate trends
        validated_trends = await self._validate_trends(trends)
        if not validated_trends:
            logger.info("No trends passed validation")
            return
        
        # 4. Summarize trends
        summarized_trends = await self._summarize_trends(validated_trends)
        
        # 5. Send notifications
        await self._send_notifications(summarized_trends)
        
        logger.info(f"News cycle completed: {len(articles)} articles, {len(summarized_trends)} trends")
    
    async def _fetch_articles(self) -> List[Article]:
        """Fetch articles from all configured sources."""
        logger.info("Fetching articles from RSS feeds")
        
        try:
            async with self.aggregator:
                articles = await self.aggregator.fetch_all_feeds()
                
                # Filter articles based on user preferences
                filtered_articles = self.aggregator.filter_articles(
                    articles,
                    min_reliability=self.user_preferences.get("min_reliability_score", 0.7),
                    max_age_hours=24
                )
                
                # Validate individual articles
                validated_articles = []
                async with self.fact_checker:
                    for article in filtered_articles:
                        validation_result = await self.fact_checker.validate_article(article)
                        if validation_result["is_valid"]:
                            validated_articles.append(article)
                
                self.processed_articles.extend(validated_articles)
                logger.info(f"Fetched and validated {len(validated_articles)} articles")
                
                return validated_articles
                
        except Exception as e:
            logger.error(f"Error fetching articles: {e}")
            return []
    
    async def _detect_trends(self, articles: List[Article]) -> List[Trend]:
        """Detect trending stories from articles."""
        logger.info("Detecting trends from articles")
        
        try:
            trends = self.trend_analyzer.detect_trends(articles)
            
            # Filter trends based on user preferences
            filtered_trends = []
            user_topics = self.user_preferences.get("topics_of_interest", [])
            
            for trend in trends:
                # Check if trend category matches user interests
                if not user_topics or trend.category.value in user_topics:
                    filtered_trends.append(trend)
            
            self.detected_trends.extend(filtered_trends)
            logger.info(f"Detected {len(filtered_trends)} trends")
            
            return filtered_trends
            
        except Exception as e:
            logger.error(f"Error detecting trends: {e}")
            return []
    
    async def _validate_trends(self, trends: List[Trend]) -> List[Trend]:
        """Validate trends for authenticity and accuracy."""
        logger.info("Validating trends")
        
        try:
            validated_trends = []
            async with self.fact_checker:
                for trend in trends:
                    validation_result = await self.fact_checker.validate_trend(trend)
                    if validation_result["is_valid"]:
                        validated_trends.append(trend)
                    else:
                        logger.info(f"Trend '{trend.title}' failed validation: {validation_result['issues']}")
            
            logger.info(f"Validated {len(validated_trends)} trends")
            return validated_trends
            
        except Exception as e:
            logger.error(f"Error validating trends: {e}")
            return []
    
    async def _summarize_trends(self, trends: List[Trend]) -> List[Trend]:
        """Generate summaries for trends."""
        logger.info("Generating trend summaries")
        
        try:
            summarized_trends = []
            for trend in trends:
                summary = await self.summarizer.summarize_trend(trend)
                if summary:
                    summarized_trends.append(trend)
                else:
                    logger.warning(f"Failed to generate summary for trend: {trend.title}")
            
            logger.info(f"Generated summaries for {len(summarized_trends)} trends")
            return summarized_trends
            
        except Exception as e:
            logger.error(f"Error summarizing trends: {e}")
            return []
    
    async def _send_notifications(self, trends: List[Trend]):
        """Send notifications for trends."""
        logger.info("Sending notifications")
        
        try:
            recipient = self.user_preferences.get("whatsapp_recipient")
            if not recipient:
                logger.warning("No WhatsApp recipient configured")
                return
            
            # Check notification frequency
            frequency = self.user_preferences.get("notification_frequency", "instant")
            
            if frequency == "instant":
                # Send instant alerts for high-priority trends
                for trend in trends:
                    if trend.trend_score > 0.8 and trend.confidence_score > 0.7:
                        success = await self.whatsapp_sender.send_instant_alert(trend, recipient)
                        if success:
                            self.sent_notifications.append({
                                "type": "instant_alert",
                                "trend_id": trend.id,
                                "sent_at": datetime.now()
                            })
            
            elif frequency == "hourly":
                # Send hourly summary
                if trends:
                    success = await self.whatsapp_sender.send_briefing_notification(
                        trends[:5],  # Top 5 trends
                        recipient,
                        NotificationType.TREND_UPDATE
                    )
                    if success:
                        self.sent_notifications.append({
                            "type": "hourly_summary",
                            "trend_count": len(trends),
                            "sent_at": datetime.now()
                        })
            
            logger.info(f"Sent notifications for {len(trends)} trends")
            
        except Exception as e:
            logger.error(f"Error sending notifications: {e}")
    
    async def send_scheduled_briefing(self, briefing_type: NotificationType):
        """Send a scheduled briefing (morning/evening)."""
        logger.info(f"Sending scheduled {briefing_type.value} briefing")
        
        try:
            recipient = self.user_preferences.get("whatsapp_recipient")
            if not recipient:
                logger.warning("No WhatsApp recipient configured")
                return
            
            # Get recent trends for briefing
            recent_trends = self._get_recent_trends(hours=24)
            
            if recent_trends:
                success = await self.whatsapp_sender.send_briefing_notification(
                    recent_trends[:10],  # Top 10 trends
                    recipient,
                    briefing_type
                )
                
                if success:
                    self.sent_notifications.append({
                        "type": briefing_type.value,
                        "trend_count": len(recent_trends),
                        "sent_at": datetime.now()
                    })
                    logger.info(f"{briefing_type.value} briefing sent successfully")
                else:
                    logger.error(f"Failed to send {briefing_type.value} briefing")
            else:
                logger.info(f"No recent trends for {briefing_type.value} briefing")
                
        except Exception as e:
            logger.error(f"Error sending scheduled briefing: {e}")
    
    def _get_recent_trends(self, hours: int = 24) -> List[Trend]:
        """Get trends from the last N hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [trend for trend in self.detected_trends 
                if trend.last_updated >= cutoff_time]
    
    async def _wait_for_next_cycle(self):
        """Wait for the next processing cycle."""
        # Calculate wait time based on notification frequency
        frequency = self.user_preferences.get("notification_frequency", "instant")
        
        if frequency == "instant":
            wait_time = 300  # 5 minutes
        elif frequency == "hourly":
            wait_time = 3600  # 1 hour
        else:  # daily
            wait_time = 86400  # 24 hours
        
        logger.info(f"Waiting {wait_time} seconds until next cycle")
        await asyncio.sleep(wait_time)
    
    async def _handle_error(self, error: Exception):
        """Handle errors during processing."""
        logger.error(f"Processing error: {error}")
        
        # Send error notification if configured
        try:
            recipient = self.user_preferences.get("whatsapp_recipient")
            if recipient:
                await self.whatsapp_sender.send_error_notification(
                    str(error),
                    recipient
                )
        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")
    
    def _update_metrics(self, start_time: float):
        """Update system metrics."""
        processing_time = time.time() - start_time
        
        self.metrics.articles_processed = len(self.processed_articles)
        self.metrics.trends_detected = len(self.detected_trends)
        self.metrics.notifications_sent = len(self.sent_notifications)
        self.metrics.avg_processing_time = processing_time
        self.metrics.timestamp = datetime.now()
    
    async def _cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up resources")
        
        # Clear old data
        cutoff_time = datetime.now() - timedelta(days=7)
        self.processed_articles = [article for article in self.processed_articles 
                                 if article.published_at >= cutoff_time]
        self.detected_trends = [trend for trend in self.detected_trends 
                              if trend.last_updated >= cutoff_time]
        self.sent_notifications = [notification for notification in self.sent_notifications 
                                 if notification["sent_at"] >= cutoff_time]
    
    def get_status(self) -> Dict[str, Any]:
        """Get current system status."""
        return {
            "running": self.running,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "metrics": self.metrics.dict(),
            "rate_limit_status": self.whatsapp_sender.get_rate_limit_status(),
            "processed_articles_count": len(self.processed_articles),
            "detected_trends_count": len(self.detected_trends),
            "sent_notifications_count": len(self.sent_notifications)
        }


async def main():
    """Main entry point for the news agent."""
    # Validate configuration
    if not config.validate():
        logger.error("Configuration validation failed")
        sys.exit(1)
    
    # Create and start news agent
    agent = NewsAgent()
    
    try:
        await agent.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 