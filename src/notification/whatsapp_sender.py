"""
WhatsApp Notification Sender using Twilio API.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json

from twilio.rest import Client
from twilio.base.exceptions import TwilioException
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from ..utils.models import Notification, Trend, NotificationType
from ..utils.config import config


class WhatsAppSender:
    """Sends WhatsApp notifications using Twilio API."""
    
    def __init__(self):
        """Initialize the WhatsApp sender."""
        self.config = config.get_notification_config()
        self.twilio_config = config.get_api_config("twilio")
        
        # Twilio client
        account_sid = self.twilio_config.get("account_sid")
        auth_token = self.twilio_config.get("auth_token")
        self.whatsapp_number = self.twilio_config.get("whatsapp_number")
        
        if not all([account_sid, auth_token, self.whatsapp_number]):
            raise ValueError("Twilio configuration incomplete")
        
        self.client = Client(account_sid, auth_token)
        
        # Notification settings
        self.whatsapp_config = self.config.get("whatsapp", {})
        self.max_messages_per_hour = self.whatsapp_config.get("max_messages_per_hour", 10)
        self.message_format = self.whatsapp_config.get("message_format", "markdown")
        
        # Rate limiting
        self.message_history = []
        self.rate_limit_window = timedelta(hours=1)
    
    async def send_trend_notification(self, trend: Trend, recipient: str) -> bool:
        """Send a notification for a trending story.
        
        Args:
            trend: Trend object to notify about
            recipient: WhatsApp recipient number
            
        Returns:
            True if sent successfully
        """
        try:
            logger.info(f"Sending trend notification to {recipient}: {trend.title}")
            
            # Create notification content
            content = self._create_trend_notification_content(trend)
            
            # Check rate limits
            if not self._check_rate_limit():
                logger.warning("Rate limit exceeded, skipping notification")
                return False
            
            # Send message
            success = await self._send_whatsapp_message(recipient, content)
            
            if success:
                # Record message
                self._record_message()
                logger.info(f"Trend notification sent successfully to {recipient}")
            else:
                logger.error(f"Failed to send trend notification to {recipient}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending trend notification: {e}")
            return False
    
    async def send_briefing_notification(self, trends: List[Trend], recipient: str, 
                                       notification_type: NotificationType = NotificationType.MORNING_BRIEFING) -> bool:
        """Send a briefing notification with multiple trends.
        
        Args:
            trends: List of trends to include in briefing
            recipient: WhatsApp recipient number
            notification_type: Type of briefing (morning/evening)
            
        Returns:
            True if sent successfully
        """
        try:
            logger.info(f"Sending {notification_type.value} briefing to {recipient}")
            
            # Create briefing content
            content = self._create_briefing_notification_content(trends, notification_type)
            
            # Check rate limits
            if not self._check_rate_limit():
                logger.warning("Rate limit exceeded, skipping briefing")
                return False
            
            # Send message
            success = await self._send_whatsapp_message(recipient, content)
            
            if success:
                # Record message
                self._record_message()
                logger.info(f"{notification_type.value} briefing sent successfully to {recipient}")
            else:
                logger.error(f"Failed to send {notification_type.value} briefing to {recipient}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending briefing notification: {e}")
            return False
    
    async def send_custom_notification(self, message: str, recipient: str, 
                                     title: Optional[str] = None) -> bool:
        """Send a custom notification message.
        
        Args:
            message: Message content
            recipient: WhatsApp recipient number
            title: Optional message title
            
        Returns:
            True if sent successfully
        """
        try:
            logger.info(f"Sending custom notification to {recipient}")
            
            # Format message
            if title:
                content = f"*{title}*\n\n{message}"
            else:
                content = message
            
            # Check rate limits
            if not self._check_rate_limit():
                logger.warning("Rate limit exceeded, skipping notification")
                return False
            
            # Send message
            success = await self._send_whatsapp_message(recipient, content)
            
            if success:
                # Record message
                self._record_message()
                logger.info(f"Custom notification sent successfully to {recipient}")
            else:
                logger.error(f"Failed to send custom notification to {recipient}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending custom notification: {e}")
            return False
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _send_whatsapp_message(self, recipient: str, content: str) -> bool:
        """Send a WhatsApp message using Twilio API.
        
        Args:
            recipient: Recipient WhatsApp number
            content: Message content
            
        Returns:
            True if sent successfully
        """
        try:
            # Ensure recipient has whatsapp: prefix
            if not recipient.startswith("whatsapp:"):
                recipient = f"whatsapp:{recipient}"
            
            # Send message
            message = self.client.messages.create(
                from_=self.whatsapp_number,
                body=content,
                to=recipient
            )
            
            # Check message status
            if message.sid:
                logger.info(f"WhatsApp message sent with SID: {message.sid}")
                return True
            else:
                logger.error("WhatsApp message failed - no SID returned")
                return False
                
        except TwilioException as e:
            logger.error(f"Twilio error sending WhatsApp message: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error sending WhatsApp message: {e}")
            return False
    
    def _create_trend_notification_content(self, trend: Trend) -> str:
        """Create notification content for a trending story.
        
        Args:
            trend: Trend object
            
        Returns:
            Formatted notification content
        """
        content = f"📰 *BREAKING NEWS*\n\n"
        content += f"*{trend.title}*\n\n"
        
        # Add summary if available
        if trend.summary:
            content += f"{trend.summary}\n\n"
        
        # Add metadata
        content += f"📊 *Trend Score:* {trend.trend_score:.1%}\n"
        content += f"📈 *Sources:* {trend.source_count} news outlets\n"
        content += f"🏷️ *Category:* {trend.category.value.title()}\n"
        content += f"⏰ *First seen:* {trend.first_seen.strftime('%H:%M')}\n\n"
        
        # Add confidence indicator
        if trend.confidence_score > 0.8:
            confidence_emoji = "🟢"
            confidence_text = "High"
        elif trend.confidence_score > 0.6:
            confidence_emoji = "🟡"
            confidence_text = "Medium"
        else:
            confidence_emoji = "🔴"
            confidence_text = "Low"
        
        content += f"{confidence_emoji} *Confidence:* {confidence_text} ({trend.confidence_score:.1%})\n\n"
        
        # Add key facts if available
        if trend.key_facts:
            content += "*Key Facts:*\n"
            for i, fact in enumerate(trend.key_facts[:3], 1):
                content += f"{i}. {fact}\n"
            content += "\n"
        
        # Add source links
        if trend.source_links:
            content += "*Sources:*\n"
            for i, url in enumerate(trend.source_links[:2], 1):
                content += f"{i}. {url}\n"
        
        return content
    
    def _create_briefing_notification_content(self, trends: List[Trend], 
                                            notification_type: NotificationType) -> str:
        """Create notification content for a briefing.
        
        Args:
            trends: List of trends
            notification_type: Type of briefing
            
        Returns:
            Formatted briefing content
        """
        if notification_type == NotificationType.MORNING_BRIEFING:
            title = "🌅 Morning News Briefing"
            emoji = "☀️"
        elif notification_type == NotificationType.EVENING_SUMMARY:
            title = "🌙 Evening News Summary"
            emoji = "🌆"
        else:
            title = "📰 News Briefing"
            emoji = "📊"
        
        content = f"{emoji} *{title}*\n"
        content += f"*{datetime.now().strftime('%B %d, %Y')}*\n\n"
        
        if not trends:
            content += "No trending stories to report at this time.\n\n"
            content += "*Stay informed with our next update!*"
            return content
        
        content += f"*Top {len(trends)} Trending Stories:*\n\n"
        
        for i, trend in enumerate(trends, 1):
            content += f"{i}. *{trend.title}*\n"
            
            if trend.summary:
                # Truncate summary if too long
                summary = trend.summary[:150] + "..." if len(trend.summary) > 150 else trend.summary
                content += f"   {summary}\n"
            
            content += f"   📊 Score: {trend.trend_score:.1%} | 📈 {trend.source_count} sources\n"
            
            # Add confidence indicator
            if trend.confidence_score > 0.8:
                confidence_emoji = "🟢"
            elif trend.confidence_score > 0.6:
                confidence_emoji = "🟡"
            else:
                confidence_emoji = "🔴"
            
            content += f"   {confidence_emoji} Confidence: {trend.confidence_score:.1%}\n\n"
        
        content += f"*Total trends analyzed: {len(trends)}*\n"
        content += f"*Generated at: {datetime.now().strftime('%H:%M')}*\n\n"
        content += "*Stay informed with our next update!*"
        
        return content
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits.
        
        Returns:
            True if within rate limits
        """
        now = datetime.now()
        window_start = now - self.rate_limit_window
        
        # Remove old messages from history
        self.message_history = [msg_time for msg_time in self.message_history 
                               if msg_time > window_start]
        
        # Check if we're under the limit
        return len(self.message_history) < self.max_messages_per_hour
    
    def _record_message(self):
        """Record a sent message for rate limiting."""
        self.message_history.append(datetime.now())
    
    async def send_instant_alert(self, trend: Trend, recipient: str) -> bool:
        """Send an instant alert for breaking news.
        
        Args:
            trend: Trend object
            recipient: WhatsApp recipient number
            
        Returns:
            True if sent successfully
        """
        try:
            logger.info(f"Sending instant alert to {recipient}: {trend.title}")
            
            # Create instant alert content
            content = f"🚨 *BREAKING NEWS ALERT*\n\n"
            content += f"*{trend.title}*\n\n"
            
            if trend.summary:
                content += f"{trend.summary}\n\n"
            
            content += f"📊 Trend Score: {trend.trend_score:.1%}\n"
            content += f"📈 Sources: {trend.source_count}\n"
            content += f"⏰ {trend.first_seen.strftime('%H:%M')}\n\n"
            
            if trend.source_links:
                content += f"📰 Read more: {trend.source_links[0]}"
            
            # Send with higher priority (no rate limit check for breaking news)
            success = await self._send_whatsapp_message(recipient, content)
            
            if success:
                logger.info(f"Instant alert sent successfully to {recipient}")
            else:
                logger.error(f"Failed to send instant alert to {recipient}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending instant alert: {e}")
            return False
    
    async def send_error_notification(self, error_message: str, recipient: str) -> bool:
        """Send an error notification.
        
        Args:
            error_message: Error message
            recipient: WhatsApp recipient number
            
        Returns:
            True if sent successfully
        """
        try:
            content = f"⚠️ *System Alert*\n\n"
            content += f"An error occurred in the news agent:\n\n"
            content += f"{error_message}\n\n"
            content += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Send without rate limit check for system alerts
            success = await self._send_whatsapp_message(recipient, content)
            
            if success:
                logger.info(f"Error notification sent to {recipient}")
            else:
                logger.error(f"Failed to send error notification to {recipient}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending error notification: {e}")
            return False
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status.
        
        Returns:
            Rate limit status dictionary
        """
        now = datetime.now()
        window_start = now - self.rate_limit_window
        
        # Clean up old messages
        self.message_history = [msg_time for msg_time in self.message_history 
                               if msg_time > window_start]
        
        return {
            "messages_sent": len(self.message_history),
            "max_messages": self.max_messages_per_hour,
            "window_start": window_start.isoformat(),
            "window_end": now.isoformat(),
            "can_send": len(self.message_history) < self.max_messages_per_hour
        } 