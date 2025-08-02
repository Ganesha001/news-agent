<<<<<<< HEAD
# news-agent
An AI news agent which summarizes the news and give you a message over whatapp
=======
# News Agent - Automated News Aggregation and Notification System

A sophisticated automated news agent that aggregates news from trusted sources, identifies trending stories, validates information for authenticity, and sends real-time alerts via WhatsApp.

## 🌟 Features

### 📰 News Aggregation
- **Multi-source RSS feeds** from trusted global news sources (Reuters, BBC, AP, Guardian, etc.)
- **Async processing** for high-performance article fetching
- **Automatic filtering** based on reliability scores and content quality
- **Real-time updates** with configurable refresh intervals

### 🔍 Trend Detection
- **AI-powered clustering** to identify trending stories across multiple sources
- **Keyword extraction** and frequency analysis
- **Cross-source validation** to ensure story authenticity
- **Confidence scoring** for trend reliability

### 📝 Smart Summarization
- **OpenAI GPT-4 integration** for intelligent article summarization
- **Context-aware summaries** that preserve key facts and context
- **Multi-language support** with automatic language detection
- **Customizable summary length** and format

### ✅ Fact-Checking & Validation
- **Cross-reference validation** across multiple independent sources
- **NewsGuard API integration** for source credibility assessment
- **Duplicate detection** to avoid redundant alerts
- **Content filtering** for sensitive or inappropriate content

### 📱 WhatsApp Notifications
- **Twilio WhatsApp API** integration for instant messaging
- **Rich message formatting** with emojis and markdown
- **Rate limiting** to comply with WhatsApp guidelines
- **Multiple notification types**: instant alerts, morning/evening briefings

### ⚙️ Advanced Configuration
- **Modular architecture** with clear separation of concerns
- **Environment-based configuration** for easy deployment
- **User preference management** for personalized news delivery
- **Comprehensive logging** and monitoring

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- OpenAI API key
- Twilio account (for WhatsApp integration)
- NewsGuard API key (optional, for fact-checking)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd news_agent
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp env.template .env
   # Edit .env with your API keys and preferences
   ```

4. **Configure your settings**
   ```bash
   # Edit config/config.yaml to customize news sources and preferences
   ```

### Configuration

#### Environment Variables (.env)
```bash
# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Twilio WhatsApp API Configuration
TWILIO_ACCOUNT_SID=your_twilio_account_sid_here
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# WhatsApp Recipient Number
WHATSAPP_RECIPIENT_NUMBER=whatsapp:+1234567890

# Optional: NewsGuard API for fact-checking
NEWSGUARD_API_KEY=your_newsguard_api_key_here
```

#### User Preferences (config/config.yaml)
```yaml
notifications:
  user_preferences:
    topics_of_interest: ["politics", "technology", "business", "health"]
    notification_frequency: "instant"  # instant, hourly, daily
    language: "en"
    max_articles_per_notification: 5
    include_source_links: true
    include_summaries: true
```

## 📖 Usage

### Command Line Interface

The News Agent provides a comprehensive CLI for testing and management:

```bash
# Run the news agent in continuous mode
python cli.py run

# Test individual components
python cli.py test-fetch          # Test article fetching
python cli.py test-trends         # Test trend detection
python cli.py test-summarization  # Test AI summarization
python cli.py test-validation     # Test fact-checking
python cli.py test-whatsapp       # Test WhatsApp notifications

# Send scheduled briefings
python cli.py send-briefing morning
python cli.py send-briefing evening

# System management
python cli.py status              # Show system status
python cli.py config              # Show configuration
```

### Programmatic Usage

```python
import asyncio
from src.main import NewsAgent

async def main():
    # Create and start the news agent
    agent = NewsAgent()
    await agent.start()

# Run the agent
asyncio.run(main())
```

### Testing Individual Components

```python
# Test RSS aggregation
from src.aggregators.rss_aggregator import RSSAggregator

async with RSSAggregator() as aggregator:
    articles = await aggregator.fetch_all_feeds()
    print(f"Fetched {len(articles)} articles")

# Test trend detection
from src.trend_detection.trend_analyzer import TrendAnalyzer

analyzer = TrendAnalyzer()
trends = analyzer.detect_trends(articles)
print(f"Detected {len(trends)} trends")

# Test summarization
from src.summarization.summarizer import NewsSummarizer

summarizer = NewsSummarizer()
summary = await summarizer.summarize_trend(trends[0])
print(f"Summary: {summary}")
```

## 🏗️ Architecture

The News Agent follows a modular, event-driven architecture:

```
src/
├── aggregators/          # News source aggregation
│   └── rss_aggregator.py
├── trend_detection/      # Trend analysis and clustering
│   └── trend_analyzer.py
├── summarization/        # AI-powered summarization
│   └── summarizer.py
├── validation/           # Fact-checking and validation
│   └── fact_checker.py
├── notification/         # WhatsApp notifications
│   └── whatsapp_sender.py
├── utils/               # Shared utilities and models
│   ├── models.py
│   └── config.py
└── main.py              # Main orchestrator
```

### Data Flow

1. **Aggregation**: RSS feeds are fetched concurrently from multiple sources
2. **Filtering**: Articles are filtered by reliability, age, and content quality
3. **Trend Detection**: AI clustering identifies trending stories across sources
4. **Validation**: Cross-reference validation and fact-checking
5. **Summarization**: OpenAI generates concise, accurate summaries
6. **Notification**: WhatsApp alerts are sent based on user preferences

## 🔧 Configuration Options

### News Sources
Add or modify news sources in `config/config.yaml`:

```yaml
news_sources:
  sources:
    - name: "Reuters"
      url: "https://feeds.reuters.com/reuters/topNews"
      category: "general"
      reliability_score: 0.95
      language: "en"
```

### Trend Detection
Customize trend detection parameters:

```yaml
trend_detection:
  min_article_count: 3
  time_window_hours: 24
  clustering:
    algorithm: "dbscan"
    eps: 0.3
    min_samples: 2
```

### Notification Settings
Configure notification behavior:

```yaml
notifications:
  whatsapp:
    enabled: true
    max_messages_per_hour: 10
    message_format: "markdown"
  scheduling:
    morning_briefing: "08:00"
    evening_summary: "20:00"
    instant_alerts: true
```

## 📊 Monitoring and Logging

### Logging
The system provides comprehensive logging with configurable levels:

```python
# Log levels: DEBUG, INFO, WARNING, ERROR
# Logs are written to both console and file
# File rotation: daily with 30-day retention
```

### Metrics
Track system performance with built-in metrics:

```python
status = agent.get_status()
print(f"Articles processed: {status['processed_articles_count']}")
print(f"Trends detected: {status['detected_trends_count']}")
print(f"Notifications sent: {status['sent_notifications_count']}")
```

### Error Handling
- Automatic retry mechanisms with exponential backoff
- Graceful degradation when APIs are unavailable
- Error notifications via WhatsApp for critical issues

## 🔒 Security and Privacy

### Data Protection
- **Encryption**: Sensitive data is encrypted at rest
- **Anonymization**: User data is anonymized where possible
- **Retention**: Configurable data retention policies
- **Access Control**: Secure API key management

### Rate Limiting
- **WhatsApp API**: Respects Twilio rate limits
- **OpenAI API**: Implements retry logic with backoff
- **RSS Feeds**: Concurrent request limiting

### Compliance
- **GDPR**: User data handling compliance
- **WhatsApp Business API**: Follows Twilio guidelines
- **Content Filtering**: Configurable content policies

## 🚀 Deployment

### Local Development
```bash
# Install in development mode
pip install -e .

# Run with hot reload
python cli.py run
```

### Production Deployment
```bash
# Using systemd (Linux)
sudo cp news-agent.service /etc/systemd/system/
sudo systemctl enable news-agent
sudo systemctl start news-agent

# Using Docker
docker build -t news-agent .
docker run -d --name news-agent news-agent
```

### Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "cli.py", "run"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Code formatting
black src/
flake8 src/
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Troubleshooting

**Common Issues:**

1. **OpenAI API errors**
   - Verify your API key is correct
   - Check your OpenAI account balance
   - Ensure you have access to GPT-4

2. **WhatsApp notification failures**
   - Verify Twilio credentials
   - Check recipient number format (should include country code)
   - Ensure WhatsApp Business API is enabled

3. **No trends detected**
   - Check RSS feed URLs are accessible
   - Verify minimum article count threshold
   - Review trend detection configuration

### Getting Help

- **Documentation**: Check this README and inline code comments
- **Issues**: Create an issue on GitHub for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions and ideas

## 🔮 Roadmap

### Planned Features
- [ ] Web dashboard for configuration and monitoring
- [ ] Email notifications as alternative to WhatsApp
- [ ] Multi-language support for summaries
- [ ] Advanced sentiment analysis
- [ ] Integration with more fact-checking APIs
- [ ] Mobile app for notifications
- [ ] Machine learning model for trend prediction

### Performance Improvements
- [ ] Database integration for persistent storage
- [ ] Redis caching for improved performance
- [ ] Horizontal scaling support
- [ ] Advanced rate limiting strategies

---

**Built with ❤️ for keeping you informed with accurate, timely news.** 
>>>>>>> 5a02f02 (Initial commit of news_agent project)
