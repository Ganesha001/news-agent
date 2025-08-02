"""
News Summarization using OpenAI GPT models.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

import openai
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from ..utils.models import Article, Trend
from ..utils.config import config


class NewsSummarizer:
    """Summarizes news articles and trends using OpenAI GPT models."""
    
    def __init__(self):
        """Initialize the news summarizer."""
        self.config = config.get_summarization_config()
        self.openai_config = config.get_api_config("openai")
        
        # Initialize OpenAI client
        api_key = self.openai_config.get("api_key")
        if not api_key:
            raise ValueError("OpenAI API key not configured")
        
        openai.api_key = api_key
        self.model = self.openai_config.get("model", "gpt-4")
        self.max_tokens = self.openai_config.get("max_tokens", 1000)
        self.temperature = self.openai_config.get("temperature", 0.3)
        
        # Summarization settings
        self.max_length = self.config.get("max_length", 200)
        self.include_key_facts = self.config.get("include_key_facts", True)
        self.include_source_links = self.config.get("include_source_links", True)
        self.confidence_threshold = self.config.get("confidence_threshold", 0.7)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def summarize_trend(self, trend: Trend) -> Optional[str]:
        """Generate a summary for a trending story.
        
        Args:
            trend: Trend object to summarize
            
        Returns:
            Generated summary or None if failed
        """
        try:
            logger.info(f"Generating summary for trend: {trend.title}")
            
            # Prepare articles for summarization
            articles_text = self._prepare_articles_for_summary(trend.articles)
            
            # Create prompt for trend summarization
            prompt = self._create_trend_summary_prompt(trend, articles_text)
            
            # Generate summary using OpenAI
            summary = await self._generate_summary_with_openai(prompt)
            
            if summary:
                # Update trend with summary
                trend.summary = summary
                trend.key_facts = self._extract_key_facts(trend.articles)
                trend.source_links = [article.url for article in trend.articles[:3]]  # Top 3 sources
                
                logger.info(f"Generated summary for trend: {trend.title}")
                return summary
            else:
                logger.error(f"Failed to generate summary for trend: {trend.title}")
                return None
                
        except Exception as e:
            logger.error(f"Error summarizing trend {trend.title}: {e}")
            return None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def summarize_article(self, article: Article) -> Optional[str]:
        """Generate a summary for a single article.
        
        Args:
            article: Article object to summarize
            
        Returns:
            Generated summary or None if failed
        """
        try:
            logger.info(f"Generating summary for article: {article.title}")
            
            # Create prompt for article summarization
            prompt = self._create_article_summary_prompt(article)
            
            # Generate summary using OpenAI
            summary = await self._generate_summary_with_openai(prompt)
            
            if summary:
                # Update article with summary
                article.summary = summary
                logger.info(f"Generated summary for article: {article.title}")
                return summary
            else:
                logger.error(f"Failed to generate summary for article: {article.title}")
                return None
                
        except Exception as e:
            logger.error(f"Error summarizing article {article.title}: {e}")
            return None
    
    async def summarize_multiple_articles(self, articles: List[Article]) -> Dict[str, str]:
        """Generate summaries for multiple articles concurrently.
        
        Args:
            articles: List of articles to summarize
            
        Returns:
            Dictionary mapping article IDs to summaries
        """
        logger.info(f"Generating summaries for {len(articles)} articles")
        
        # Create tasks for concurrent summarization
        tasks = [self.summarize_article(article) for article in articles]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        summaries = {}
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error summarizing article {articles[i].title}: {result}")
            elif result:
                summaries[articles[i].id] = result
        
        logger.info(f"Generated {len(summaries)} summaries")
        return summaries
    
    def _prepare_articles_for_summary(self, articles: List[Article]) -> str:
        """Prepare articles text for summarization.
        
        Args:
            articles: List of articles to prepare
            
        Returns:
            Formatted text for summarization
        """
        articles_text = []
        
        for i, article in enumerate(articles[:5], 1):  # Limit to 5 articles
            article_text = f"Article {i} - {article.source.name}:\n"
            article_text += f"Title: {article.title}\n"
            
            if article.description:
                article_text += f"Description: {article.description}\n"
            
            if article.content:
                # Truncate content if too long
                content = article.content[:1000] + "..." if len(article.content) > 1000 else article.content
                article_text += f"Content: {content}\n"
            
            article_text += f"Published: {article.published_at.strftime('%Y-%m-%d %H:%M')}\n"
            article_text += f"URL: {article.url}\n\n"
            
            articles_text.append(article_text)
        
        return "\n".join(articles_text)
    
    def _create_trend_summary_prompt(self, trend: Trend, articles_text: str) -> str:
        """Create a prompt for trend summarization.
        
        Args:
            trend: Trend object
            articles_text: Formatted articles text
            
        Returns:
            Prompt for OpenAI
        """
        prompt = f"""You are a professional news analyst. Analyze the following trending news story and create a concise, accurate summary.

TRENDING STORY:
Title: {trend.title}
Category: {trend.category.value}
Keywords: {', '.join(trend.keywords)}
Article Count: {trend.article_count}
Source Count: {trend.source_count}
Trend Score: {trend.trend_score:.2f}
Confidence Score: {trend.confidence_score:.2f}

ARTICLES:
{articles_text}

INSTRUCTIONS:
1. Create a concise summary (maximum {self.max_length} characters)
2. Focus on the most important facts and developments
3. Maintain objectivity and accuracy
4. Include key details that make this story significant
5. Avoid speculation or opinion
6. Use clear, professional language

SUMMARY:"""
        
        return prompt
    
    def _create_article_summary_prompt(self, article: Article) -> str:
        """Create a prompt for article summarization.
        
        Args:
            article: Article object
            
        Returns:
            Prompt for OpenAI
        """
        content = article.content or article.description or ""
        if len(content) > 1000:
            content = content[:1000] + "..."
        
        prompt = f"""You are a professional news analyst. Create a concise summary of the following news article.

ARTICLE:
Title: {article.title}
Source: {article.source.name}
Category: {article.category.value}
Published: {article.published_at.strftime('%Y-%m-%d %H:%M')}

Content:
{content}

INSTRUCTIONS:
1. Create a concise summary (maximum {self.max_length} characters)
2. Focus on the most important facts
3. Maintain objectivity and accuracy
4. Use clear, professional language
5. Avoid speculation or opinion

SUMMARY:"""
        
        return prompt
    
    async def _generate_summary_with_openai(self, prompt: str) -> Optional[str]:
        """Generate summary using OpenAI API.
        
        Args:
            prompt: Prompt for the model
            
        Returns:
            Generated summary or None if failed
        """
        try:
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional news analyst specializing in creating accurate, concise summaries."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                timeout=30
            )
            
            summary = response.choices[0].message.content.strip()
            
            # Validate summary
            if self._validate_summary(summary):
                return summary
            else:
                logger.warning("Generated summary failed validation")
                return None
                
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            return None
    
    def _validate_summary(self, summary: str) -> bool:
        """Validate the generated summary.
        
        Args:
            summary: Generated summary text
            
        Returns:
            True if summary is valid
        """
        if not summary or len(summary.strip()) < 10:
            return False
        
        if len(summary) > self.max_length * 2:  # Allow some flexibility
            return False
        
        # Check for common issues
        issues = [
            "I apologize",
            "I cannot",
            "I'm unable",
            "I don't have",
            "I'm sorry"
        ]
        
        for issue in issues:
            if issue.lower() in summary.lower():
                return False
        
        return True
    
    def _extract_key_facts(self, articles: List[Article]) -> List[str]:
        """Extract key facts from articles.
        
        Args:
            articles: List of articles
            
        Returns:
            List of key facts
        """
        facts = []
        
        # Extract facts from titles and descriptions
        for article in articles[:3]:  # Limit to 3 articles
            # Extract named entities and important phrases
            text = f"{article.title} {article.description or ''}"
            
            # Simple fact extraction (in a real implementation, you might use NER)
            sentences = text.split('.')
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 20 and len(sentence) < 200:
                    # Look for sentences with numbers, dates, or proper nouns
                    if any(char.isdigit() for char in sentence) or any(word[0].isupper() for word in sentence.split()):
                        facts.append(sentence)
                        if len(facts) >= 5:  # Limit to 5 facts
                            break
        
        return facts[:5]  # Return top 5 facts
    
    def create_notification_summary(self, trend: Trend) -> str:
        """Create a formatted summary for notifications.
        
        Args:
            trend: Trend object
            
        Returns:
            Formatted notification summary
        """
        if not trend.summary:
            return f"📰 {trend.title}\n\nNo summary available."
        
        # Create notification format
        notification = f"📰 *{trend.title}*\n\n"
        notification += f"{trend.summary}\n\n"
        
        # Add metadata
        notification += f"📊 *Trend Score:* {trend.trend_score:.1%}\n"
        notification += f"📈 *Sources:* {trend.source_count} news outlets\n"
        notification += f"📅 *First seen:* {trend.first_seen.strftime('%H:%M')}\n"
        
        # Add category
        notification += f"🏷️ *Category:* {trend.category.value.title()}\n\n"
        
        # Add key facts if available
        if trend.key_facts and self.include_key_facts:
            notification += "*Key Facts:*\n"
            for i, fact in enumerate(trend.key_facts[:3], 1):
                notification += f"{i}. {fact}\n"
            notification += "\n"
        
        # Add source links if enabled
        if trend.source_links and self.include_source_links:
            notification += "*Sources:*\n"
            for i, url in enumerate(trend.source_links[:2], 1):
                notification += f"{i}. {url}\n"
        
        return notification
    
    def create_briefing_summary(self, trends: List[Trend]) -> str:
        """Create a briefing summary for multiple trends.
        
        Args:
            trends: List of trends
            
        Returns:
            Formatted briefing summary
        """
        if not trends:
            return "📰 *Morning Briefing*\n\nNo trending stories to report."
        
        briefing = f"📰 *Morning Briefing - {datetime.now().strftime('%B %d, %Y')}*\n\n"
        briefing += f"*Top {len(trends)} Trending Stories:*\n\n"
        
        for i, trend in enumerate(trends, 1):
            briefing += f"{i}. *{trend.title}*\n"
            if trend.summary:
                summary = trend.summary[:100] + "..." if len(trend.summary) > 100 else trend.summary
                briefing += f"   {summary}\n"
            briefing += f"   📊 Score: {trend.trend_score:.1%} | 📈 {trend.source_count} sources\n\n"
        
        briefing += f"*Total trends analyzed: {len(trends)}*\n"
        briefing += f"*Generated at: {datetime.now().strftime('%H:%M')}*"
        
        return briefing 