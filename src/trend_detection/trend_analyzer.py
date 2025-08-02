"""
Trend Detection and Analysis for identifying trending news stories.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter, defaultdict
import re
import hashlib

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd

from loguru import logger

from ..utils.models import Article, Trend, ArticleCategory
from ..utils.config import config


class TrendAnalyzer:
    """Analyzes news articles to identify trending stories."""
    
    def __init__(self):
        """Initialize the trend analyzer."""
        self.config = config.get_trend_detection_config()
        self.min_article_count = self.config.get("min_article_count", 3)
        self.time_window_hours = self.config.get("time_window_hours", 24)
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2
        )
    
    def detect_trends(self, articles: List[Article]) -> List[Trend]:
        """Detect trending stories from a list of articles.
        
        Args:
            articles: List of articles to analyze
            
        Returns:
            List of detected trends
        """
        if len(articles) < self.min_article_count:
            logger.info(f"Insufficient articles for trend detection: {len(articles)}")
            return []
        
        logger.info(f"Analyzing {len(articles)} articles for trends")
        
        # Filter articles by time window
        recent_articles = self._filter_by_time_window(articles)
        if len(recent_articles) < self.min_article_count:
            logger.info(f"Insufficient recent articles for trend detection: {len(recent_articles)}")
            return []
        
        # Extract features and cluster articles
        clusters = self._cluster_articles(recent_articles)
        
        # Convert clusters to trends
        trends = []
        for cluster in clusters:
            if len(cluster) >= self.min_article_count:
                trend = self._create_trend_from_cluster(cluster)
                if trend:
                    trends.append(trend)
        
        # Sort trends by score
        trends.sort(key=lambda x: x.trend_score, reverse=True)
        
        logger.info(f"Detected {len(trends)} trends")
        return trends
    
    def _filter_by_time_window(self, articles: List[Article]) -> List[Article]:
        """Filter articles to only include those within the time window.
        
        Args:
            articles: List of articles to filter
            
        Returns:
            Filtered list of articles
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.time_window_hours)
        recent_articles = [article for article in articles if article.published_at >= cutoff_time]
        
        logger.info(f"Filtered to {len(recent_articles)} recent articles")
        return recent_articles
    
    def _cluster_articles(self, articles: List[Article]) -> List[List[Article]]:
        """Cluster articles based on content similarity.
        
        Args:
            articles: List of articles to cluster
            
        Returns:
            List of article clusters
        """
        if len(articles) < 2:
            return [articles]
        
        # Prepare text data for clustering
        texts = []
        for article in articles:
            text = f"{article.title} {article.description or ''} {' '.join(article.keywords)}"
            texts.append(text)
        
        try:
            # Create TF-IDF vectors
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            
            # Perform clustering
            clustering_config = self.config.get("clustering", {})
            eps = clustering_config.get("eps", 0.3)
            min_samples = clustering_config.get("min_samples", 2)
            
            dbscan = DBSCAN(eps=eps, min_samples=min_samples, metric='cosine')
            cluster_labels = dbscan.fit_predict(tfidf_matrix)
            
            # Group articles by cluster
            clusters = defaultdict(list)
            for i, label in enumerate(cluster_labels):
                clusters[label].append(articles[i])
            
            # Convert to list and filter out noise (label -1)
            result_clusters = [cluster for label, cluster in clusters.items() if label != -1]
            
            logger.info(f"Created {len(result_clusters)} clusters from {len(articles)} articles")
            return result_clusters
            
        except Exception as e:
            logger.error(f"Error in clustering: {e}")
            # Fallback: group by similar titles
            return self._fallback_clustering(articles)
    
    def _fallback_clustering(self, articles: List[Article]) -> List[List[Article]]:
        """Fallback clustering method based on title similarity.
        
        Args:
            articles: List of articles to cluster
            
        Returns:
            List of article clusters
        """
        clusters = []
        processed = set()
        
        for i, article1 in enumerate(articles):
            if i in processed:
                continue
            
            cluster = [article1]
            processed.add(i)
            
            # Find similar articles
            for j, article2 in enumerate(articles[i+1:], i+1):
                if j in processed:
                    continue
                
                if self._are_articles_similar(article1, article2):
                    cluster.append(article2)
                    processed.add(j)
            
            if len(cluster) >= self.min_article_count:
                clusters.append(cluster)
        
        return clusters
    
    def _are_articles_similar(self, article1: Article, article2: Article) -> bool:
        """Check if two articles are similar based on title and keywords.
        
        Args:
            article1: First article
            article2: Second article
            
        Returns:
            True if articles are similar
        """
        # Compare titles
        title1 = article1.title.lower()
        title2 = article2.title.lower()
        
        # Simple similarity check
        common_words = set(title1.split()) & set(title2.split())
        if len(common_words) >= 2:
            return True
        
        # Compare keywords
        common_keywords = set(article1.keywords) & set(article2.keywords)
        if len(common_keywords) >= 2:
            return True
        
        return False
    
    def _create_trend_from_cluster(self, cluster: List[Article]) -> Optional[Trend]:
        """Create a trend object from a cluster of articles.
        
        Args:
            cluster: List of articles in the cluster
            
        Returns:
            Trend object or None if creation fails
        """
        try:
            # Basic trend information
            article_count = len(cluster)
            source_count = len(set(article.source.name for article in cluster))
            
            # Generate trend title
            title = self._generate_trend_title(cluster)
            
            # Generate description
            description = self._generate_trend_description(cluster)
            
            # Extract keywords
            keywords = self._extract_trend_keywords(cluster)
            
            # Determine category
            category = self._determine_trend_category(cluster)
            
            # Calculate trend score
            trend_score = self._calculate_trend_score(cluster)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(cluster)
            
            # Temporal data
            first_seen = min(article.published_at for article in cluster)
            last_updated = max(article.published_at for article in cluster)
            duration_hours = (last_updated - first_seen).total_seconds() / 3600
            
            # Generate trend ID
            trend_id = self._generate_trend_id(cluster)
            
            trend = Trend(
                id=trend_id,
                title=title,
                description=description,
                keywords=keywords,
                articles=cluster,
                category=category,
                article_count=article_count,
                source_count=source_count,
                trend_score=trend_score,
                confidence_score=confidence_score,
                first_seen=first_seen,
                last_updated=last_updated,
                duration_hours=duration_hours
            )
            
            return trend
            
        except Exception as e:
            logger.error(f"Error creating trend from cluster: {e}")
            return None
    
    def _generate_trend_title(self, cluster: List[Article]) -> str:
        """Generate a title for the trend based on cluster articles.
        
        Args:
            cluster: List of articles in the cluster
            
        Returns:
            Trend title
        """
        # Use the most common words from titles
        all_words = []
        for article in cluster:
            words = re.findall(r'\b\w+\b', article.title.lower())
            all_words.extend(words)
        
        # Count word frequencies
        word_counts = Counter(all_words)
        
        # Filter out common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can'}
        filtered_words = [(word, count) for word, count in word_counts.items() 
                         if word not in stop_words and len(word) > 3]
        
        # Sort by frequency and take top words
        filtered_words.sort(key=lambda x: x[1], reverse=True)
        top_words = [word for word, _ in filtered_words[:3]]
        
        if top_words:
            return " ".join(top_words).title()
        else:
            # Fallback to first article title
            return cluster[0].title[:50] + "..." if len(cluster[0].title) > 50 else cluster[0].title
    
    def _generate_trend_description(self, cluster: List[Article]) -> str:
        """Generate a description for the trend.
        
        Args:
            cluster: List of articles in the cluster
            
        Returns:
            Trend description
        """
        # Use the most recent article's description
        recent_article = max(cluster, key=lambda x: x.published_at)
        if recent_article.description:
            return recent_article.description[:200] + "..." if len(recent_article.description) > 200 else recent_article.description
        
        # Fallback to title
        return f"Trending story: {recent_article.title}"
    
    def _extract_trend_keywords(self, cluster: List[Article]) -> List[str]:
        """Extract keywords for the trend from cluster articles.
        
        Args:
            cluster: List of articles in the cluster
            
        Returns:
            List of keywords
        """
        all_keywords = []
        for article in cluster:
            all_keywords.extend(article.keywords)
        
        # Count keyword frequencies
        keyword_counts = Counter(all_keywords)
        
        # Return top keywords
        max_keywords = self.config.get("keyword_extraction", {}).get("max_keywords", 10)
        return [keyword for keyword, _ in keyword_counts.most_common(max_keywords)]
    
    def _determine_trend_category(self, cluster: List[Article]) -> ArticleCategory:
        """Determine the category for the trend.
        
        Args:
            cluster: List of articles in the cluster
            
        Returns:
            Trend category
        """
        # Count categories
        category_counts = Counter(article.category for article in cluster)
        
        # Return most common category
        return category_counts.most_common(1)[0][0]
    
    def _calculate_trend_score(self, cluster: List[Article]) -> float:
        """Calculate a trend score based on various factors.
        
        Args:
            cluster: List of articles in the cluster
            
        Returns:
            Trend score between 0 and 1
        """
        # Factors to consider:
        # 1. Number of articles
        # 2. Number of sources
        # 3. Average reliability score
        # 4. Recency of articles
        # 5. Source diversity
        
        article_count = len(cluster)
        source_count = len(set(article.source.name for article in cluster))
        avg_reliability = np.mean([article.reliability_score for article in cluster])
        
        # Calculate recency score
        now = datetime.now(timezone.utc)
        recency_scores = []
        for article in cluster:
            hours_old = (now - article.published_at).total_seconds() / 3600
            recency_score = max(0, 1 - (hours_old / self.time_window_hours))
            recency_scores.append(recency_score)
        avg_recency = np.mean(recency_scores)
        
        # Normalize factors
        article_score = min(1.0, article_count / 10)  # Cap at 10 articles
        source_score = min(1.0, source_count / 5)     # Cap at 5 sources
        
        # Weighted combination
        trend_score = (
            0.3 * article_score +
            0.3 * source_score +
            0.2 * avg_reliability +
            0.2 * avg_recency
        )
        
        return min(1.0, trend_score)
    
    def _calculate_confidence_score(self, cluster: List[Article]) -> float:
        """Calculate confidence score for the trend.
        
        Args:
            cluster: List of articles in the cluster
            
        Returns:
            Confidence score between 0 and 1
        """
        # Factors for confidence:
        # 1. Source reliability
        # 2. Content consistency
        # 3. Cross-referencing
        
        # Average source reliability
        avg_reliability = np.mean([article.reliability_score for article in cluster])
        
        # Content consistency (similar titles)
        title_similarity = self._calculate_title_similarity(cluster)
        
        # Cross-referencing (multiple sources)
        source_diversity = min(1.0, len(set(article.source.name for article in cluster)) / 3)
        
        confidence_score = (
            0.4 * avg_reliability +
            0.3 * title_similarity +
            0.3 * source_diversity
        )
        
        return min(1.0, confidence_score)
    
    def _calculate_title_similarity(self, cluster: List[Article]) -> float:
        """Calculate similarity between article titles in the cluster.
        
        Args:
            cluster: List of articles in the cluster
            
        Returns:
            Similarity score between 0 and 1
        """
        if len(cluster) < 2:
            return 1.0
        
        titles = [article.title.lower() for article in cluster]
        
        # Simple word overlap similarity
        similarities = []
        for i in range(len(titles)):
            for j in range(i + 1, len(titles)):
                words1 = set(titles[i].split())
                words2 = set(titles[j].split())
                
                if len(words1 | words2) > 0:
                    similarity = len(words1 & words2) / len(words1 | words2)
                    similarities.append(similarity)
        
        return np.mean(similarities) if similarities else 0.0
    
    def _generate_trend_id(self, cluster: List[Article]) -> str:
        """Generate a unique ID for the trend.
        
        Args:
            cluster: List of articles in the cluster
            
        Returns:
            Unique trend ID
        """
        # Use keywords and first article to generate ID
        keywords_str = "_".join(sorted(self._extract_trend_keywords(cluster)[:5]))
        first_article_id = cluster[0].id or cluster[0].title
        
        id_string = f"{keywords_str}_{first_article_id}"
        return hashlib.md5(id_string.encode()).hexdigest() 