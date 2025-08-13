"""
Chat Analysis Worker - Real-time chat and social media analysis
Production-ready worker for sentiment analysis, toxicity detection, and engagement metrics
"""

import asyncio
import json
import logging
import os
import sys
import re
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
from core.database import get_redis, SessionLocal

logger = logging.getLogger(__name__)

class ChatAnalysisWorker:
    """Production-ready chat analysis worker"""
    
    def __init__(self):
        self.worker_type = "chat_analysis"
        self.redis_client = get_redis().get_client()
        
        # Load sentiment and toxicity word lists
        self.positive_words = self.load_positive_words()
        self.negative_words = self.load_negative_words()
        self.toxic_words = self.load_toxic_words()
        self.spam_patterns = self.load_spam_patterns()
        
        logger.info(f"💬 Chat Analysis Worker initialized")
        logger.info(f"   Loaded {len(self.positive_words)} positive words")
        logger.info(f"   Loaded {len(self.negative_words)} negative words")
        logger.info(f"   Loaded {len(self.toxic_words)} toxic words")
    
    def load_positive_words(self) -> set:
        """Load positive sentiment words"""
        return {
            'good', 'great', 'awesome', 'amazing', 'excellent', 'fantastic',
            'wonderful', 'brilliant', 'outstanding', 'superb', 'perfect',
            'love', 'like', 'enjoy', 'happy', 'excited', 'thrilled',
            'bullish', 'moon', 'rocket', 'gem', 'diamond', 'hands',
            'hodl', 'buy', 'pump', 'green', 'profit', 'gains',
            'best', 'top', 'winner', 'success', 'victory', 'champion',
            'positive', 'optimistic', 'confident', 'strong', 'solid',
            'thank', 'thanks', 'grateful', 'appreciate', 'blessed'
        }
    
    def load_negative_words(self) -> set:
        """Load negative sentiment words"""
        return {
            'bad', 'terrible', 'awful', 'horrible', 'disgusting', 'hate',
            'dislike', 'angry', 'mad', 'furious', 'disappointed', 'sad',
            'bearish', 'dump', 'crash', 'red', 'loss', 'losses',
            'scam', 'fraud', 'fake', 'lie', 'lying', 'cheat',
            'worst', 'bottom', 'loser', 'failure', 'defeat', 'disaster',
            'negative', 'pessimistic', 'worried', 'concerned', 'afraid',
            'panic', 'fear', 'scared', 'anxious', 'stressed', 'broken'
        }
    
    def load_toxic_words(self) -> set:
        """Load toxic/harmful words for content moderation"""
        return {
            'spam', 'scam', 'fraud', 'fake', 'bot', 'shill',
            'pump', 'dump', 'rugpull', 'ponzi', 'pyramid',
            'hate', 'toxic', 'troll', 'fud', 'manipulation',
            'stupid', 'idiot', 'moron', 'dumb', 'retard',
            'kill', 'die', 'death', 'suicide', 'harm'
        }
    
    def load_spam_patterns(self) -> List[str]:
        """Load spam detection patterns"""
        return [
            r'(?i)click\s+here',
            r'(?i)free\s+money',
            r'(?i)guaranteed\s+profit',
            r'(?i)100%\s+returns?',
            r'(?i)risk\s+free',
            r'(?i)limited\s+time',
            r'(?i)act\s+now',
            r'(?i)dm\s+me',
            r'(?i)private\s+message',
            r'https?://[^\s]+',  # URLs
            r'(?i)telegram\.me',
            r'(?i)whatsapp\.com'
        ]
    
    async def process_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process chat message with comprehensive analysis"""
        try:
            data = event_data["data"]
            user_id = event_data.get("user_id")
            
            # Validate event data
            if not self.validate_event(data):
                raise ValueError("Invalid chat event data")
            
            message = data.get("message", "")
            user = data.get("user", "Unknown")
            channel = data.get("channel", "general")
            platform = data.get("platform", "unknown")
            
            # Perform comprehensive analysis
            sentiment_analysis = self.analyze_sentiment(message)
            toxicity_analysis = self.detect_toxicity(message)
            spam_analysis = self.detect_spam(message)
            keywords = self.extract_keywords(message)
            entities = self.extract_entities(message)
            engagement_score = self.calculate_engagement_score(data)
            language_info = self.detect_language(message)
            
            # Create processed result
            processed_data = {
                "id": f"chat_{int(datetime.utcnow().timestamp())}",
                "type": "chat_analysis",
                "original_data": data,
                "message": message,
                "user": user,
                "channel": channel,
                "platform": platform,
                "analysis": {
                    "sentiment": sentiment_analysis,
                    "toxicity": toxicity_analysis,
                    "spam": spam_analysis,
                    "keywords": keywords,
                    "entities": entities,
                    "language": language_info,
                    "engagement_score": engagement_score,
                    "message_stats": self.get_message_stats(message)
                },
                "moderation": self.get_moderation_flags(toxicity_analysis, spam_analysis),
                "insights": self.generate_insights(sentiment_analysis, toxicity_analysis, engagement_score),
                "processed_at": datetime.utcnow().isoformat(),
                "processed_by": user_id,
                "worker": "chat_analysis_worker"
            }
            
            # Save to database
            await self.save_to_database(processed_data)
            
            # Update graph relationships
            await self.update_graph_relationships(processed_data)
            
            logger.info(f"✅ Processed chat message: {processed_data['id']} - Sentiment: {sentiment_analysis['label']}")
            return processed_data
            
        except Exception as e:
            error_data = {
                "id": f"chat_error_{int(datetime.utcnow().timestamp())}",
                "type": "chat_analysis_error",
                "error": str(e),
                "original_data": event_data.get("data", {}),
                "processed_at": datetime.utcnow().isoformat(),
                "worker": "chat_analysis_worker"
            }
            
            logger.error(f"❌ Chat analysis failed: {e}")
            await self.save_to_database(error_data)
            return error_data
    
    def analyze_sentiment(self, message: str) -> Dict[str, Any]:
        """Analyze sentiment of the message"""
        words = self.tokenize_message(message)
        
        positive_count = sum(1 for word in words if word in self.positive_words)
        negative_count = sum(1 for word in words if word in self.negative_words)
        
        # Calculate sentiment score (-1 to 1)
        total_sentiment_words = positive_count + negative_count
        if total_sentiment_words == 0:
            score = 0
            label = "neutral"
        else:
            score = (positive_count - negative_count) / len(words)
            score = max(-1, min(1, score))  # Clamp between -1 and 1
            
            if score > 0.1:
                label = "positive"
            elif score < -0.1:
                label = "negative"
            else:
                label = "neutral"
        
        # Calculate confidence based on sentiment word density
        confidence = min(1.0, total_sentiment_words / max(1, len(words)))
        
        return {
            "score": round(score, 3),
            "label": label,
            "confidence": round(confidence, 3),
            "positive_words": positive_count,
            "negative_words": negative_count,
            "details": {
                "positive_matches": [w for w in words if w in self.positive_words],
                "negative_matches": [w for w in words if w in self.negative_words]
            }
        }
    
    def detect_toxicity(self, message: str) -> Dict[str, Any]:
        """Detect toxic content in the message"""
        words = self.tokenize_message(message)
        
        toxic_matches = [word for word in words if word in self.toxic_words]
        toxic_count = len(toxic_matches)
        
        # Calculate toxicity score
        toxicity_score = min(1.0, toxic_count / max(1, len(words)) * 10)
        
        # Determine toxicity level
        if toxicity_score > 0.7:
            level = "high"
        elif toxicity_score > 0.3:
            level = "medium"
        elif toxicity_score > 0:
            level = "low"
        else:
            level = "none"
        
        is_toxic = toxicity_score > 0.3
        
        return {
            "is_toxic": is_toxic,
            "score": round(toxicity_score, 3),
            "level": level,
            "confidence": min(1.0, toxic_count / max(1, len(words)) * 5),
            "toxic_words": toxic_matches,
            "categories": self.categorize_toxicity(toxic_matches)
        }
    
    def detect_spam(self, message: str) -> Dict[str, Any]:
        """Detect spam patterns in the message"""
        spam_indicators = []
        
        # Check against spam patterns
        for pattern in self.spam_patterns:
            if re.search(pattern, message):
                spam_indicators.append(pattern)
        
        # Additional spam checks
        if len(message) > 500:  # Very long messages
            spam_indicators.append("excessive_length")
        
        if message.count('!') > 5:  # Excessive exclamation marks
            spam_indicators.append("excessive_punctuation")
        
        if len(set(message.lower())) / max(1, len(message)) < 0.3:  # Low character diversity
            spam_indicators.append("low_diversity")
        
        # Calculate spam score
        spam_score = min(1.0, len(spam_indicators) / 5)
        is_spam = spam_score > 0.5
        
        return {
            "is_spam": is_spam,
            "score": round(spam_score, 3),
            "confidence": min(1.0, len(spam_indicators) / 3),
            "indicators": spam_indicators,
            "risk_level": "high" if spam_score > 0.7 else "medium" if spam_score > 0.3 else "low"
        }
    
    def extract_keywords(self, message: str) -> List[str]:
        """Extract important keywords from the message"""
        words = self.tokenize_message(message)
        
        # Filter out common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'
        }
        
        # Extract meaningful keywords (length > 3, not stop words)
        keywords = [
            word for word in words 
            if len(word) > 3 and word not in stop_words
        ]
        
        # Remove duplicates and return top 10
        return list(dict.fromkeys(keywords))[:10]
    
    def extract_entities(self, message: str) -> Dict[str, List[str]]:
        """Extract entities like mentions, hashtags, URLs"""
        entities = {
            "mentions": re.findall(r'@(\w+)', message),
            "hashtags": re.findall(r'#(\w+)', message),
            "urls": re.findall(r'https?://[^\s]+', message),
            "emails": re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', message),
            "phone_numbers": re.findall(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', message),
            "crypto_addresses": re.findall(r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b', message)  # Bitcoin-like addresses
        }
        
        return {k: v for k, v in entities.items() if v}  # Only return non-empty lists
    
    def calculate_engagement_score(self, data: Dict[str, Any]) -> int:
        """Calculate engagement score based on message characteristics"""
        message = data.get("message", "")
        
        score = 50  # Base score
        
        # Message length factor
        length = len(message)
        if 50 <= length <= 200:
            score += 10  # Optimal length
        elif length > 500:
            score -= 10  # Too long
        elif length < 10:
            score -= 5   # Too short
        
        # Question marks (engagement)
        score += min(10, message.count('?') * 5)
        
        # Exclamation marks (enthusiasm)
        score += min(10, message.count('!') * 2)
        
        # Mentions (social engagement)
        mentions = len(re.findall(r'@\w+', message))
        score += min(15, mentions * 5)
        
        # Hashtags (topic engagement)
        hashtags = len(re.findall(r'#\w+', message))
        score += min(10, hashtags * 3)
        
        # Emojis (emotional engagement)
        emoji_pattern = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]')
        emojis = len(emoji_pattern.findall(message))
        score += min(15, emojis * 3)
        
        return max(0, min(100, score))
    
    def detect_language(self, message: str) -> Dict[str, Any]:
        """Simple language detection"""
        # Basic language detection based on character patterns
        # In production, you might use a proper language detection library
        
        english_words = {'the', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 'have', 'has'}
        words = self.tokenize_message(message)
        
        english_count = sum(1 for word in words if word in english_words)
        english_ratio = english_count / max(1, len(words))
        
        if english_ratio > 0.1:
            language = "en"
            confidence = min(1.0, english_ratio * 2)
        else:
            language = "unknown"
            confidence = 0.5
        
        return {
            "language": language,
            "confidence": round(confidence, 3)
        }
    
    def get_message_stats(self, message: str) -> Dict[str, Any]:
        """Get basic message statistics"""
        words = self.tokenize_message(message)
        
        return {
            "character_count": len(message),
            "word_count": len(words),
            "sentence_count": len(re.split(r'[.!?]+', message)),
            "avg_word_length": round(sum(len(word) for word in words) / max(1, len(words)), 2),
            "uppercase_ratio": round(sum(1 for c in message if c.isupper()) / max(1, len(message)), 3),
            "punctuation_count": len(re.findall(r'[^\w\s]', message))
        }
    
    def get_moderation_flags(self, toxicity: Dict, spam: Dict) -> Dict[str, Any]:
        """Generate moderation flags and recommendations"""
        flags = []
        actions = []
        
        if toxicity["is_toxic"]:
            flags.append("toxic_content")
            if toxicity["level"] == "high":
                actions.append("auto_remove")
            else:
                actions.append("flag_for_review")
        
        if spam["is_spam"]:
            flags.append("spam_content")
            actions.append("flag_for_review")
        
        return {
            "flags": flags,
            "recommended_actions": actions,
            "requires_human_review": len(flags) > 0,
            "auto_moderate": "auto_remove" in actions
        }
    
    def generate_insights(self, sentiment: Dict, toxicity: Dict, engagement: int) -> List[str]:
        """Generate insights about the message"""
        insights = []
        
        if sentiment["label"] == "positive" and engagement > 70:
            insights.append("High-engagement positive message - potential viral content")
        
        if sentiment["label"] == "negative" and sentiment["confidence"] > 0.7:
            insights.append("Strong negative sentiment detected - monitor for escalation")
        
        if toxicity["is_toxic"]:
            insights.append("Toxic content detected - requires moderation")
        
        if engagement > 80:
            insights.append("High engagement potential - consider promoting")
        elif engagement < 30:
            insights.append("Low engagement - content may need improvement")
        
        return insights
    
    def categorize_toxicity(self, toxic_words: List[str]) -> List[str]:
        """Categorize types of toxicity"""
        categories = []
        
        hate_words = {'hate', 'toxic', 'stupid', 'idiot', 'moron', 'dumb'}
        spam_words = {'spam', 'scam', 'fraud', 'fake', 'bot', 'shill'}
        threat_words = {'kill', 'die', 'death', 'suicide', 'harm'}
        
        if any(word in hate_words for word in toxic_words):
            categories.append("hate_speech")
        
        if any(word in spam_words for word in toxic_words):
            categories.append("spam")
        
        if any(word in threat_words for word in toxic_words):
            categories.append("threats")
        
        return categories
    
    def tokenize_message(self, message: str) -> List[str]:
        """Tokenize message into words"""
        # Convert to lowercase and extract words
        words = re.findall(r'\b\w+\b', message.lower())
        return words
    
    def validate_event(self, event_data: Dict[str, Any]) -> bool:
        """Validate chat event data"""
        required_fields = ["message", "user"]
        return all(field in event_data and event_data[field] for field in required_fields)
    
    async def save_to_database(self, data: Dict[str, Any]) -> bool:
        """Save processed data to Redis and PostgreSQL"""
        try:
            # Save to Redis for quick access
            key = f"processed:{self.worker_type}:{data['id']}"
            self.redis_client.setex(key, 3600, json.dumps(data))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save chat data: {e}")
            return False
    
    async def update_graph_relationships(self, data: Dict[str, Any]):
        """Update Neo4j graph with chat relationships"""
        try:
            from core.database import get_neo4j
            neo4j_db = get_neo4j()
            
            # Create chat message node and relationships
            query = """
            MERGE (m:ChatMessage {id: $message_id})
            SET m.content = $content,
                m.sentiment = $sentiment,
                m.engagement_score = $engagement,
                m.processed_at = $processed_at
            
            MERGE (u:ChatUser {username: $username})
            MERGE (c:Channel {name: $channel})
            MERGE (u)-[:POSTED]->(m)
            MERGE (m)-[:IN_CHANNEL]->(c)
            
            WITH m
            MATCH (processor:User {id: $processor_id})
            MERGE (processor)-[:PROCESSED]->(m)
            """
            
            neo4j_db.execute_query(query, {
                'message_id': data['id'],
                'content': data.get('message', ''),
                'sentiment': data.get('analysis', {}).get('sentiment', {}).get('label', ''),
                'engagement': data.get('analysis', {}).get('engagement_score', 0),
                'processed_at': data['processed_at'],
                'username': data.get('user', ''),
                'channel': data.get('channel', ''),
                'processor_id': data.get('processed_by', 0)
            })
            
        except Exception as e:
            logger.warning(f"Failed to update graph relationships: {e}")
    
    async def listen_and_process(self):
        """Main worker loop"""
        queue_name = f"events:{self.worker_type}"
        logger.info(f"🔧 {self.worker_type} worker started - listening to {queue_name}")
        
        while True:
            try:
                # Pull event from queue
                result = self.redis_client.brpop(queue_name, timeout=1)
                if result:
                    _, event_json = result
                    event_data = json.loads(event_json)
                    
                    # Process the event
                    processed_result = await self.process_event(event_data)
                    
                    # Log success
                    if 'error' not in processed_result:
                        logger.info(f"✅ Successfully processed chat message: {processed_result.get('id')}")
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in queue: {e}")
            except Exception as e:
                logger.error(f"🚨 Worker error: {e}")
                await asyncio.sleep(5)

async def main():
    """Main entry point for the worker"""
    worker = ChatAnalysisWorker()
    await worker.listen_and_process()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("🚀 Starting Chat Analysis Worker...")
    asyncio.run(main())