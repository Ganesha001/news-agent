"""
Fact Checking and Validation for news articles and trends.
"""

import asyncio
import aiohttp
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import hashlib
import re

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from ..utils.models import Article, Trend
from ..utils.config import config


class FactChecker:
    """Validates news articles and trends for authenticity and accuracy."""
    
    def __init__(self):
        """Initialize the fact checker."""
        self.config = config.get_validation_config()
        self.newsguard_config = config.get_api_config("newsguard")
        
        # Validation settings
        self.cross_reference_threshold = self.config.get("cross_reference_threshold", 2)
        self.fact_check_enabled = self.config.get("fact_check_enabled", True)
        self.duplicate_detection = self.config.get("duplicate_detection", True)
        
        # Content filtering
        self.content_filtering = self.config.get("content_filtering", {})
        self.blocked_keywords = self.content_filtering.get("blocked_keywords", [])
        self.sensitive_topics = self.content_filtering.get("sensitive_topics", [])
        
        # Session for HTTP requests
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def validate_trend(self, trend: Trend) -> Dict[str, Any]:
        """Validate a trending story for authenticity and accuracy.
        
        Args:
            trend: Trend object to validate
            
        Returns:
            Validation results dictionary
        """
        logger.info(f"Validating trend: {trend.title}")
        
        validation_results = {
            "is_valid": True,
            "confidence_score": 0.0,
            "cross_reference_score": 0.0,
            "fact_check_score": 0.0,
            "duplicate_check": False,
            "content_filter": True,
            "issues": [],
            "validated_at": datetime.now()
        }
        
        try:
            # 1. Cross-reference validation
            cross_ref_result = await self._cross_reference_validation(trend)
            validation_results["cross_reference_score"] = cross_ref_result["score"]
            validation_results["issues"].extend(cross_ref_result["issues"])
            
            # 2. Fact-checking (if enabled)
            if self.fact_check_enabled:
                fact_check_result = await self._fact_check_validation(trend)
                validation_results["fact_check_score"] = fact_check_result["score"]
                validation_results["issues"].extend(fact_check_result["issues"])
            
            # 3. Duplicate detection
            if self.duplicate_detection:
                duplicate_result = self._duplicate_detection(trend)
                validation_results["duplicate_check"] = duplicate_result["is_duplicate"]
                validation_results["issues"].extend(duplicate_result["issues"])
            
            # 4. Content filtering
            content_filter_result = self._content_filter_validation(trend)
            validation_results["content_filter"] = content_filter_result["passed"]
            validation_results["issues"].extend(content_filter_result["issues"])
            
            # 5. Calculate overall confidence
            validation_results["confidence_score"] = self._calculate_confidence_score(validation_results)
            
            # 6. Determine if trend is valid
            validation_results["is_valid"] = self._determine_validity(validation_results)
            
            # Update trend with validation results
            trend.confidence_score = validation_results["confidence_score"]
            
            logger.info(f"Validation completed for trend: {trend.title} - Score: {validation_results['confidence_score']:.2f}")
            
        except Exception as e:
            logger.error(f"Error validating trend {trend.title}: {e}")
            validation_results["is_valid"] = False
            validation_results["issues"].append(f"Validation error: {str(e)}")
        
        return validation_results
    
    async def validate_article(self, article: Article) -> Dict[str, Any]:
        """Validate a single article for authenticity and accuracy.
        
        Args:
            article: Article object to validate
            
        Returns:
            Validation results dictionary
        """
        logger.info(f"Validating article: {article.title}")
        
        validation_results = {
            "is_valid": True,
            "confidence_score": 0.0,
            "source_reliability": article.source.reliability_score,
            "content_filter": True,
            "issues": [],
            "validated_at": datetime.now()
        }
        
        try:
            # 1. Source reliability check
            source_result = self._source_reliability_check(article)
            validation_results["source_reliability"] = source_result["score"]
            validation_results["issues"].extend(source_result["issues"])
            
            # 2. Content filtering
            content_filter_result = self._content_filter_validation_article(article)
            validation_results["content_filter"] = content_filter_result["passed"]
            validation_results["issues"].extend(content_filter_result["issues"])
            
            # 3. Calculate confidence score
            validation_results["confidence_score"] = self._calculate_article_confidence(validation_results)
            
            # 4. Determine if article is valid
            validation_results["is_valid"] = self._determine_article_validity(validation_results)
            
            # Update article with validation results
            article.reliability_score = validation_results["confidence_score"]
            
            logger.info(f"Validation completed for article: {article.title} - Score: {validation_results['confidence_score']:.2f}")
            
        except Exception as e:
            logger.error(f"Error validating article {article.title}: {e}")
            validation_results["is_valid"] = False
            validation_results["issues"].append(f"Validation error: {str(e)}")
        
        return validation_results
    
    async def _cross_reference_validation(self, trend: Trend) -> Dict[str, Any]:
        """Cross-reference trend across multiple sources.
        
        Args:
            trend: Trend object to validate
            
        Returns:
            Cross-reference validation results
        """
        results = {
            "score": 0.0,
            "issues": [],
            "source_agreement": 0.0
        }
        
        try:
            # Check if we have enough sources
            if trend.source_count < self.cross_reference_threshold:
                results["issues"].append(f"Insufficient sources: {trend.source_count} < {self.cross_reference_threshold}")
                results["score"] = 0.3
                return results
            
            # Analyze source diversity
            source_names = [article.source.name for article in trend.articles]
            unique_sources = len(set(source_names))
            
            # Calculate source agreement score
            source_agreement = min(1.0, unique_sources / 5.0)  # Normalize to 5 sources
            results["source_agreement"] = source_agreement
            
            # Check for source reliability
            avg_reliability = sum(article.source.reliability_score for article in trend.articles) / len(trend.articles)
            
            # Calculate cross-reference score
            results["score"] = (source_agreement * 0.6) + (avg_reliability * 0.4)
            
            if results["score"] < 0.5:
                results["issues"].append("Low cross-reference confidence")
            
        except Exception as e:
            logger.error(f"Error in cross-reference validation: {e}")
            results["issues"].append(f"Cross-reference error: {str(e)}")
            results["score"] = 0.0
        
        return results
    
    async def _fact_check_validation(self, trend: Trend) -> Dict[str, Any]:
        """Perform fact-checking using external APIs.
        
        Args:
            trend: Trend object to validate
            
        Returns:
            Fact-check validation results
        """
        results = {
            "score": 0.0,
            "issues": [],
            "fact_check_results": []
        }
        
        try:
            # Check if NewsGuard API is available
            if not self.newsguard_config.get("enabled"):
                results["issues"].append("NewsGuard API not enabled")
                results["score"] = 0.5  # Neutral score
                return results
            
            # Perform fact-checking on key claims
            fact_check_results = []
            for article in trend.articles[:3]:  # Check top 3 articles
                fact_check = await self._check_article_facts(article)
                fact_check_results.append(fact_check)
            
            # Calculate average fact-check score
            if fact_check_results:
                avg_score = sum(result["score"] for result in fact_check_results) / len(fact_check_results)
                results["score"] = avg_score
                results["fact_check_results"] = fact_check_results
                
                if avg_score < 0.7:
                    results["issues"].append("Low fact-check confidence")
            else:
                results["score"] = 0.5  # Neutral score
                results["issues"].append("No fact-check results available")
            
        except Exception as e:
            logger.error(f"Error in fact-check validation: {e}")
            results["issues"].append(f"Fact-check error: {str(e)}")
            results["score"] = 0.0
        
        return results
    
    async def _check_article_facts(self, article: Article) -> Dict[str, Any]:
        """Check facts in a single article using NewsGuard API.
        
        Args:
            article: Article object to check
            
        Returns:
            Fact-check results
        """
        results = {
            "article_id": article.id,
            "score": 0.5,
            "issues": [],
            "checked_at": datetime.now()
        }
        
        try:
            if not self.session:
                raise RuntimeError("Session not initialized")
            
            # Extract domain from URL
            domain = self._extract_domain(str(article.url))
            if not domain:
                results["issues"].append("Could not extract domain from URL")
                return results
            
            # Call NewsGuard API (placeholder - implement actual API call)
            # In a real implementation, you would call the NewsGuard API here
            # For now, we'll use a simple heuristic based on source reliability
            
            if article.source.reliability_score > 0.8:
                results["score"] = 0.9
            elif article.source.reliability_score > 0.6:
                results["score"] = 0.7
            else:
                results["score"] = 0.4
                results["issues"].append("Low source reliability")
            
        except Exception as e:
            logger.error(f"Error checking facts for article {article.id}: {e}")
            results["issues"].append(f"Fact-check error: {str(e)}")
            results["score"] = 0.0
        
        return results
    
    def _duplicate_detection(self, trend: Trend) -> Dict[str, Any]:
        """Detect duplicate or very similar trends.
        
        Args:
            trend: Trend object to check
            
        Returns:
            Duplicate detection results
        """
        results = {
            "is_duplicate": False,
            "issues": [],
            "similarity_score": 0.0
        }
        
        try:
            # Generate trend fingerprint
            trend_fingerprint = self._generate_trend_fingerprint(trend)
            
            # In a real implementation, you would check against a database of existing trends
            # For now, we'll use a simple heuristic
            
            # Check for very similar titles
            title_words = set(trend.title.lower().split())
            if len(title_words) < 3:
                results["issues"].append("Very short title - potential duplicate")
                results["similarity_score"] = 0.8
            
            # Check for repeated keywords
            if len(set(trend.keywords)) < 2:
                results["issues"].append("Very few unique keywords")
                results["similarity_score"] = 0.7
            
            # Determine if it's a duplicate
            if results["similarity_score"] > 0.8:
                results["is_duplicate"] = True
                results["issues"].append("High similarity to existing content")
            
        except Exception as e:
            logger.error(f"Error in duplicate detection: {e}")
            results["issues"].append(f"Duplicate detection error: {str(e)}")
        
        return results
    
    def _content_filter_validation(self, trend: Trend) -> Dict[str, Any]:
        """Filter content based on blocked keywords and sensitive topics.
        
        Args:
            trend: Trend object to filter
            
        Returns:
            Content filter results
        """
        results = {
            "passed": True,
            "issues": [],
            "blocked_keywords_found": [],
            "sensitive_topics_found": []
        }
        
        try:
            # Check for blocked keywords
            trend_text = f"{trend.title} {trend.description} {' '.join(trend.keywords)}".lower()
            
            for keyword in self.blocked_keywords:
                if keyword.lower() in trend_text:
                    results["blocked_keywords_found"].append(keyword)
                    results["passed"] = False
            
            # Check for sensitive topics
            for topic in self.sensitive_topics:
                if topic.lower() in trend_text:
                    results["sensitive_topics_found"].append(topic)
                    # Don't automatically fail for sensitive topics, just flag them
            
            if results["blocked_keywords_found"]:
                results["issues"].append(f"Blocked keywords found: {', '.join(results['blocked_keywords_found'])}")
            
            if results["sensitive_topics_found"]:
                results["issues"].append(f"Sensitive topics detected: {', '.join(results['sensitive_topics_found'])}")
            
        except Exception as e:
            logger.error(f"Error in content filter validation: {e}")
            results["issues"].append(f"Content filter error: {str(e)}")
            results["passed"] = False
        
        return results
    
    def _content_filter_validation_article(self, article: Article) -> Dict[str, Any]:
        """Filter article content based on blocked keywords and sensitive topics.
        
        Args:
            article: Article object to filter
            
        Returns:
            Content filter results
        """
        results = {
            "passed": True,
            "issues": [],
            "blocked_keywords_found": [],
            "sensitive_topics_found": []
        }
        
        try:
            # Check for blocked keywords
            article_text = f"{article.title} {article.description or ''} {article.content or ''}".lower()
            
            for keyword in self.blocked_keywords:
                if keyword.lower() in article_text:
                    results["blocked_keywords_found"].append(keyword)
                    results["passed"] = False
            
            # Check for sensitive topics
            for topic in self.sensitive_topics:
                if topic.lower() in article_text:
                    results["sensitive_topics_found"].append(topic)
            
            if results["blocked_keywords_found"]:
                results["issues"].append(f"Blocked keywords found: {', '.join(results['blocked_keywords_found'])}")
            
            if results["sensitive_topics_found"]:
                results["issues"].append(f"Sensitive topics detected: {', '.join(results['sensitive_topics_found'])}")
            
        except Exception as e:
            logger.error(f"Error in article content filter validation: {e}")
            results["issues"].append(f"Content filter error: {str(e)}")
            results["passed"] = False
        
        return results
    
    def _source_reliability_check(self, article: Article) -> Dict[str, Any]:
        """Check the reliability of the article's source.
        
        Args:
            article: Article object to check
            
        Returns:
            Source reliability results
        """
        results = {
            "score": article.source.reliability_score,
            "issues": []
        }
        
        try:
            # Check source reliability score
            if article.source.reliability_score < 0.5:
                results["issues"].append("Low source reliability score")
            
            # Check if source is active
            if not article.source.is_active:
                results["issues"].append("Source is marked as inactive")
                results["score"] *= 0.5
            
            # Additional checks could include:
            # - Domain age
            # - SSL certificate
            # - Social media presence
            # - Editorial standards
            
        except Exception as e:
            logger.error(f"Error in source reliability check: {e}")
            results["issues"].append(f"Source reliability check error: {str(e)}")
            results["score"] = 0.0
        
        return results
    
    def _calculate_confidence_score(self, validation_results: Dict[str, Any]) -> float:
        """Calculate overall confidence score from validation results.
        
        Args:
            validation_results: Validation results dictionary
            
        Returns:
            Confidence score between 0 and 1
        """
        try:
            # Weighted combination of different validation scores
            cross_ref_weight = 0.4
            fact_check_weight = 0.3
            content_filter_weight = 0.2
            duplicate_weight = 0.1
            
            # Base score from cross-reference
            score = validation_results["cross_reference_score"] * cross_ref_weight
            
            # Add fact-check score if available
            if validation_results["fact_check_score"] > 0:
                score += validation_results["fact_check_score"] * fact_check_weight
            
            # Content filter penalty
            if not validation_results["content_filter"]:
                score *= 0.5
            
            # Duplicate penalty
            if validation_results["duplicate_check"]:
                score *= 0.3
            
            # Issue penalty
            issue_penalty = min(0.2, len(validation_results["issues"]) * 0.05)
            score = max(0.0, score - issue_penalty)
            
            return min(1.0, score)
            
        except Exception as e:
            logger.error(f"Error calculating confidence score: {e}")
            return 0.0
    
    def _calculate_article_confidence(self, validation_results: Dict[str, Any]) -> float:
        """Calculate confidence score for a single article.
        
        Args:
            validation_results: Validation results dictionary
            
        Returns:
            Confidence score between 0 and 1
        """
        try:
            # Weighted combination
            source_weight = 0.7
            content_filter_weight = 0.3
            
            score = validation_results["source_reliability"] * source_weight
            
            # Content filter penalty
            if not validation_results["content_filter"]:
                score *= 0.5
            
            # Issue penalty
            issue_penalty = min(0.2, len(validation_results["issues"]) * 0.05)
            score = max(0.0, score - issue_penalty)
            
            return min(1.0, score)
            
        except Exception as e:
            logger.error(f"Error calculating article confidence score: {e}")
            return 0.0
    
    def _determine_validity(self, validation_results: Dict[str, Any]) -> bool:
        """Determine if a trend is valid based on validation results.
        
        Args:
            validation_results: Validation results dictionary
            
        Returns:
            True if trend is valid
        """
        # Must pass content filter
        if not validation_results["content_filter"]:
            return False
        
        # Must have minimum confidence score
        if validation_results["confidence_score"] < 0.5:
            return False
        
        # Must not be a duplicate
        if validation_results["duplicate_check"]:
            return False
        
        # Must have sufficient cross-reference
        if validation_results["cross_reference_score"] < 0.3:
            return False
        
        return True
    
    def _determine_article_validity(self, validation_results: Dict[str, Any]) -> bool:
        """Determine if an article is valid based on validation results.
        
        Args:
            validation_results: Validation results dictionary
            
        Returns:
            True if article is valid
        """
        # Must pass content filter
        if not validation_results["content_filter"]:
            return False
        
        # Must have minimum confidence score
        if validation_results["confidence_score"] < 0.4:
            return False
        
        return True
    
    def _generate_trend_fingerprint(self, trend: Trend) -> str:
        """Generate a fingerprint for trend comparison.
        
        Args:
            trend: Trend object
            
        Returns:
            Trend fingerprint string
        """
        # Create a fingerprint based on title and keywords
        fingerprint_data = f"{trend.title.lower()} {' '.join(sorted(trend.keywords))}"
        return hashlib.md5(fingerprint_data.encode()).hexdigest()
    
    def _extract_domain(self, url: str) -> Optional[str]:
        """Extract domain from URL.
        
        Args:
            url: URL string
            
        Returns:
            Domain string or None
        """
        try:
            # Simple domain extraction
            if url.startswith(('http://', 'https://')):
                domain = url.split('/')[2]
            else:
                domain = url.split('/')[0]
            
            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            
            return domain
        except Exception:
            return None 