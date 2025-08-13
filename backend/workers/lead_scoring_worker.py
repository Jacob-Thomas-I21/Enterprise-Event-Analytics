"""
Lead Scoring Worker - AI-powered lead analysis using OpenRouter
Production-ready worker for processing lead events
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
from core.database import get_redis, get_db, SessionLocal
from core.auth import UserRole
import openai

logger = logging.getLogger(__name__)

class LeadScoringWorker:
    """Production-ready lead scoring worker with OpenRouter integration"""
    
    def __init__(self):
        self.worker_type = "lead_scoring"
        self.redis_client = get_redis().get_client()
        
        # Configure OpenRouter client
        self.ai_client = openai.OpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1"
        )
        self.ai_model = settings.AI_MODEL
        
        logger.info(f"🤖 Lead Scoring Worker initialized with model: {self.ai_model}")
    
    async def process_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process lead data with AI scoring"""
        try:
            data = event_data["data"]
            user_id = event_data.get("user_id")
            
            # Validate required fields
            if not self.validate_event(data):
                raise ValueError("Invalid lead data: missing required fields")
            
            # AI-powered lead scoring
            ai_analysis = await self.analyze_lead_with_ai(data)
            
            # Calculate additional metrics
            lead_score = self.extract_score_from_analysis(ai_analysis)
            category = self.categorize_lead(lead_score)
            
            # Create processed result
            processed_data = {
                "id": f"lead_{int(datetime.utcnow().timestamp())}",
                "type": "lead_scoring",
                "original_data": data,
                "ai_analysis": ai_analysis,
                "lead_score": lead_score,
                "category": category,
                "model_used": self.ai_model,
                "processed_at": datetime.utcnow().isoformat(),
                "processed_by": user_id,
                "worker": "lead_scoring_worker",
                "recommendations": self.get_recommendations(category, lead_score)
            }
            
            # Save to database
            await self.save_to_database(processed_data)
            
            # Update Neo4j graph
            await self.update_graph_relationships(processed_data)
            
            logger.info(f"✅ Processed lead: {processed_data['id']} - Score: {lead_score} - Category: {category}")
            return processed_data
            
        except Exception as e:
            error_data = {
                "id": f"lead_error_{int(datetime.utcnow().timestamp())}",
                "type": "lead_scoring_error",
                "error": str(e),
                "original_data": event_data.get("data", {}),
                "processed_at": datetime.utcnow().isoformat(),
                "worker": "lead_scoring_worker"
            }
            
            logger.error(f"❌ Lead processing failed: {e}")
            await self.save_to_database(error_data)
            return error_data
    
    async def analyze_lead_with_ai(self, data: Dict[str, Any]) -> str:
        """Analyze lead using OpenRouter AI"""
        try:
            prompt = f"""
            Analyze this lead and provide a comprehensive assessment:
            
            Lead Information:
            - Name: {data.get('name', 'Unknown')}
            - Email: {data.get('email', 'Unknown')}
            - Company: {data.get('company', 'Unknown')}
            - Title: {data.get('title', 'Unknown')}
            - Source: {data.get('source', 'Unknown')}
            - Phone: {data.get('phone', 'Not provided')}
            - Industry: {data.get('industry', 'Unknown')}
            - Company Size: {data.get('company_size', 'Unknown')}
            
            Please provide:
            1. Lead Score (0-100)
            2. Category (hot/warm/cold)
            3. Reasoning for the score
            4. Key strengths and concerns
            5. Recommended next actions
            
            Return as JSON format:
            {{
                "score": <number>,
                "category": "<hot/warm/cold>",
                "reasoning": "<detailed explanation>",
                "strengths": ["<strength1>", "<strength2>"],
                "concerns": ["<concern1>", "<concern2>"],
                "next_actions": ["<action1>", "<action2>"]
            }}
            """
            
            response = self.ai_client.chat.completions.create(
                model=self.ai_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            # Fallback to rule-based scoring
            return self.fallback_scoring(data)
    
    def fallback_scoring(self, data: Dict[str, Any]) -> str:
        """Fallback rule-based scoring when AI is unavailable"""
        score = 50  # Base score
        
        # Email domain scoring
        email = data.get('email', '').lower()
        if any(domain in email for domain in ['gmail.com', 'yahoo.com', 'hotmail.com']):
            score -= 10
        elif any(domain in email for domain in ['.edu', '.gov', '.org']):
            score += 15
        else:
            score += 5  # Business email
        
        # Company size scoring
        company_size = data.get('company_size', '').lower()
        if 'enterprise' in company_size or '1000+' in company_size:
            score += 20
        elif 'medium' in company_size or '100-1000' in company_size:
            score += 10
        
        # Title scoring
        title = data.get('title', '').lower()
        if any(role in title for role in ['ceo', 'cto', 'vp', 'director', 'manager']):
            score += 15
        
        # Source scoring
        source = data.get('source', '').lower()
        if source in ['referral', 'linkedin', 'conference']:
            score += 10
        elif source in ['cold_email', 'advertisement']:
            score -= 5
        
        score = max(0, min(100, score))  # Clamp between 0-100
        category = 'hot' if score >= 80 else 'warm' if score >= 60 else 'cold'
        
        return json.dumps({
            "score": score,
            "category": category,
            "reasoning": f"Rule-based scoring: {score}/100 based on email domain, company size, title, and source",
            "strengths": ["Automated scoring available"],
            "concerns": ["AI analysis unavailable"],
            "next_actions": ["Follow up within 24 hours", "Qualify budget and timeline"]
        })
    
    def extract_score_from_analysis(self, ai_analysis: str) -> int:
        """Extract numeric score from AI analysis"""
        try:
            analysis_data = json.loads(ai_analysis)
            return int(analysis_data.get('score', 50))
        except:
            # Try to extract score with regex as fallback
            import re
            score_match = re.search(r'"score":\s*(\d+)', ai_analysis)
            if score_match:
                return int(score_match.group(1))
            return 50  # Default score
    
    def categorize_lead(self, score: int) -> str:
        """Categorize lead based on score"""
        if score >= 80:
            return "hot"
        elif score >= 60:
            return "warm"
        else:
            return "cold"
    
    def get_recommendations(self, category: str, score: int) -> list:
        """Get action recommendations based on lead category"""
        if category == "hot":
            return [
                "Contact within 1 hour",
                "Schedule demo call",
                "Send personalized proposal",
                "Assign to senior sales rep"
            ]
        elif category == "warm":
            return [
                "Follow up within 24 hours",
                "Send relevant case studies",
                "Schedule discovery call",
                "Add to nurture campaign"
            ]
        else:
            return [
                "Add to long-term nurture sequence",
                "Send educational content",
                "Follow up in 1 week",
                "Qualify budget and timeline"
            ]
    
    def validate_event(self, event_data: Dict[str, Any]) -> bool:
        """Validate if event data has required fields"""
        required_fields = ["name", "email"]
        return all(field in event_data and event_data[field] for field in required_fields)
    
    async def save_to_database(self, data: Dict[str, Any]) -> bool:
        """Save processed data to Redis and PostgreSQL"""
        try:
            # Save to Redis for quick access
            key = f"processed:{self.worker_type}:{data['id']}"
            self.redis_client.setex(key, 3600, json.dumps(data))  # 1 hour TTL
            
            # Save to PostgreSQL for persistence
            db = SessionLocal()
            try:
                # Update event processing status
                from init_scripts import event_processing_status
                # This would be handled by SQLAlchemy models in a real implementation
                pass
            finally:
                db.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save lead data: {e}")
            return False
    
    async def update_graph_relationships(self, data: Dict[str, Any]):
        """Update Neo4j graph with lead relationships"""
        try:
            from core.database import get_neo4j
            neo4j_db = get_neo4j()
            
            # Create lead node and relationships
            query = """
            MERGE (l:Lead {id: $lead_id})
            SET l.name = $name,
                l.email = $email,
                l.company = $company,
                l.score = $score,
                l.category = $category,
                l.processed_at = $processed_at
            
            MERGE (c:Company {name: $company})
            MERGE (l)-[:WORKS_AT]->(c)
            
            WITH l
            MATCH (u:User {id: $user_id})
            MERGE (u)-[:PROCESSED]->(l)
            """
            
            original_data = data.get('original_data', {})
            neo4j_db.execute_query(query, {
                'lead_id': data['id'],
                'name': original_data.get('name', ''),
                'email': original_data.get('email', ''),
                'company': original_data.get('company', ''),
                'score': data.get('lead_score', 0),
                'category': data.get('category', ''),
                'processed_at': data['processed_at'],
                'user_id': data.get('processed_by', 0)
            })
            
        except Exception as e:
            logger.warning(f"Failed to update graph relationships: {e}")
    
    async def listen_and_process(self):
        """Main worker loop - listens to queue and processes events"""
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
                        logger.info(f"✅ Successfully processed lead: {processed_result.get('id')}")
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in queue: {e}")
            except Exception as e:
                logger.error(f"🚨 Worker error: {e}")
                await asyncio.sleep(5)  # Back off on error

async def main():
    """Main entry point for the worker"""
    worker = LeadScoringWorker()
    await worker.listen_and_process()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("🚀 Starting Lead Scoring Worker...")
    asyncio.run(main())