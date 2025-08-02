#!/usr/bin/env python3
"""
Command Line Interface for the News Agent
"""

import asyncio
import argparse
import sys
from pathlib import Path

from src.main import NewsAgent
from src.utils.config import config
from src.utils.models import NotificationType
from loguru import logger


async def run_agent():
    """Run the news agent in continuous mode."""
    agent = NewsAgent()
    await agent.start()


async def test_fetch():
    """Test article fetching."""
    from src.aggregators.rss_aggregator import RSSAggregator
    
    logger.info("Testing article fetching...")
    
    async with RSSAggregator() as aggregator:
        articles = await aggregator.fetch_all_feeds()
        
        print(f"\n📰 Fetched {len(articles)} articles:")
        for i, article in enumerate(articles[:5], 1):
            print(f"{i}. {article.title}")
            print(f"   Source: {article.source.name}")
            print(f"   Published: {article.published_at}")
            print(f"   URL: {article.url}")
            print()


async def test_trends():
    """Test trend detection."""
    from src.aggregators.rss_aggregator import RSSAggregator
    from src.trend_detection.trend_analyzer import TrendAnalyzer
    
    logger.info("Testing trend detection...")
    
    # Fetch articles
    async with RSSAggregator() as aggregator:
        articles = await aggregator.fetch_all_feeds()
        filtered_articles = aggregator.filter_articles(articles)
    
    # Detect trends
    analyzer = TrendAnalyzer()
    trends = analyzer.detect_trends(filtered_articles)
    
    print(f"\n📈 Detected {len(trends)} trends:")
    for i, trend in enumerate(trends[:5], 1):
        print(f"{i}. {trend.title}")
        print(f"   Score: {trend.trend_score:.2f}")
        print(f"   Sources: {trend.source_count}")
        print(f"   Articles: {trend.article_count}")
        print(f"   Category: {trend.category.value}")
        print()


async def test_summarization():
    """Test summarization."""
    from src.aggregators.rss_aggregator import RSSAggregator
    from src.trend_detection.trend_analyzer import TrendAnalyzer
    from src.summarization.summarizer import NewsSummarizer
    
    logger.info("Testing summarization...")
    
    # Fetch and detect trends
    async with RSSAggregator() as aggregator:
        articles = await aggregator.fetch_all_feeds()
        filtered_articles = aggregator.filter_articles(articles)
    
    analyzer = TrendAnalyzer()
    trends = analyzer.detect_trends(filtered_articles)
    
    if not trends:
        print("No trends detected for summarization test")
        return
    
    # Summarize trends
    summarizer = NewsSummarizer()
    trend = trends[0]  # Test with first trend
    
    summary = await summarizer.summarize_trend(trend)
    
    print(f"\n📝 Summary for: {trend.title}")
    print(f"Summary: {summary}")
    print()


async def test_validation():
    """Test validation."""
    from src.aggregators.rss_aggregator import RSSAggregator
    from src.trend_detection.trend_analyzer import TrendAnalyzer
    from src.validation.fact_checker import FactChecker
    
    logger.info("Testing validation...")
    
    # Fetch and detect trends
    async with RSSAggregator() as aggregator:
        articles = await aggregator.fetch_all_feeds()
        filtered_articles = aggregator.filter_articles(articles)
    
    analyzer = TrendAnalyzer()
    trends = analyzer.detect_trends(filtered_articles)
    
    if not trends:
        print("No trends detected for validation test")
        return
    
    # Validate trends
    async with FactChecker() as fact_checker:
        trend = trends[0]  # Test with first trend
        validation_result = await fact_checker.validate_trend(trend)
        
        print(f"\n🔍 Validation for: {trend.title}")
        print(f"Valid: {validation_result['is_valid']}")
        print(f"Confidence: {validation_result['confidence_score']:.2f}")
        print(f"Cross-reference score: {validation_result['cross_reference_score']:.2f}")
        print(f"Fact-check score: {validation_result['fact_check_score']:.2f}")
        print(f"Issues: {validation_result['issues']}")
        print()


async def test_whatsapp():
    """Test WhatsApp notifications."""
    from src.notification.whatsapp_sender import WhatsAppSender
    
    logger.info("Testing WhatsApp notifications...")
    
    try:
        sender = WhatsAppSender()
        
        # Test custom message
        recipient = config.get_user_preferences().get("whatsapp_recipient")
        if not recipient:
            print("No WhatsApp recipient configured. Please set WHATSAPP_RECIPIENT_NUMBER in your .env file")
            return
        
        success = await sender.send_custom_notification(
            "This is a test message from the News Agent! 🚀",
            recipient,
            "Test Notification"
        )
        
        if success:
            print("✅ WhatsApp test message sent successfully!")
        else:
            print("❌ Failed to send WhatsApp test message")
            
    except Exception as e:
        print(f"❌ Error testing WhatsApp: {e}")


async def send_briefing(briefing_type: str):
    """Send a briefing notification."""
    agent = NewsAgent()
    
    if briefing_type == "morning":
        notification_type = NotificationType.MORNING_BRIEFING
    elif briefing_type == "evening":
        notification_type = NotificationType.EVENING_SUMMARY
    else:
        print(f"Invalid briefing type: {briefing_type}")
        return
    
    await agent.send_scheduled_briefing(notification_type)


def show_status():
    """Show system status."""
    agent = NewsAgent()
    status = agent.get_status()
    
    print("\n📊 News Agent Status:")
    print(f"Running: {status['running']}")
    print(f"Last run: {status['last_run']}")
    print(f"Processed articles: {status['processed_articles_count']}")
    print(f"Detected trends: {status['detected_trends_count']}")
    print(f"Sent notifications: {status['sent_notifications_count']}")
    
    metrics = status['metrics']
    print(f"\n📈 Metrics:")
    print(f"Average processing time: {metrics['avg_processing_time']:.2f}s")
    print(f"API requests: {metrics['api_requests']}")
    print(f"Errors: {metrics['errors_count']}")
    
    rate_limit = status['rate_limit_status']
    print(f"\n📱 Rate Limit Status:")
    print(f"Messages sent: {rate_limit['messages_sent']}/{rate_limit['max_messages']}")
    print(f"Can send: {rate_limit['can_send']}")


def show_config():
    """Show current configuration."""
    print("\n⚙️ Current Configuration:")
    
    # News sources
    sources = config.get_news_sources()
    print(f"\n📰 News Sources ({len(sources)}):")
    for source in sources:
        print(f"  - {source['name']}: {source['url']}")
    
    # User preferences
    prefs = config.get_user_preferences()
    print(f"\n👤 User Preferences:")
    print(f"  Topics: {', '.join(prefs.get('topics_of_interest', []))}")
    print(f"  Frequency: {prefs.get('notification_frequency', 'instant')}")
    print(f"  Language: {prefs.get('language', 'en')}")
    
    # API configuration
    apis = config.get("apis", {})
    print(f"\n🔑 API Configuration:")
    for api_name, api_config in apis.items():
        if api_name == "openai":
            print(f"  OpenAI: {'Configured' if api_config.get('api_key') else 'Not configured'}")
        elif api_name == "twilio":
            print(f"  Twilio: {'Configured' if api_config.get('account_sid') else 'Not configured'}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="News Agent - Automated News Aggregation and Notification System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py run                    # Run the news agent
  python cli.py test-fetch             # Test article fetching
  python cli.py test-trends            # Test trend detection
  python cli.py test-summarization     # Test summarization
  python cli.py test-validation        # Test validation
  python cli.py test-whatsapp          # Test WhatsApp notifications
  python cli.py send-briefing morning  # Send morning briefing
  python cli.py status                 # Show system status
  python cli.py config                 # Show configuration
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Run command
    subparsers.add_parser("run", help="Run the news agent in continuous mode")
    
    # Test commands
    subparsers.add_parser("test-fetch", help="Test article fetching")
    subparsers.add_parser("test-trends", help="Test trend detection")
    subparsers.add_parser("test-summarization", help="Test summarization")
    subparsers.add_parser("test-validation", help="Test validation")
    subparsers.add_parser("test-whatsapp", help="Test WhatsApp notifications")
    
    # Briefing command
    briefing_parser = subparsers.add_parser("send-briefing", help="Send a briefing notification")
    briefing_parser.add_argument("type", choices=["morning", "evening"], help="Type of briefing")
    
    # Status command
    subparsers.add_parser("status", help="Show system status")
    
    # Config command
    subparsers.add_parser("config", help="Show current configuration")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute command
    try:
        if args.command == "run":
            asyncio.run(run_agent())
        elif args.command == "test-fetch":
            asyncio.run(test_fetch())
        elif args.command == "test-trends":
            asyncio.run(test_trends())
        elif args.command == "test-summarization":
            asyncio.run(test_summarization())
        elif args.command == "test-validation":
            asyncio.run(test_validation())
        elif args.command == "test-whatsapp":
            asyncio.run(test_whatsapp())
        elif args.command == "send-briefing":
            asyncio.run(send_briefing(args.type))
        elif args.command == "status":
            show_status()
        elif args.command == "config":
            show_config()
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        logger.error(f"Error executing command '{args.command}': {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 