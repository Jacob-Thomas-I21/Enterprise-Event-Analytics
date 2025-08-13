"""
Analytics API routes for data visualization and insights
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import logging

from core.database import get_db, get_redis, get_neo4j
from core.auth import get_current_user, require_analyst
from models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/dashboard")
async def get_dashboard_data(current_user: User = Depends(require_analyst)):
    """Get dashboard overview data"""
    try:
        redis_client = get_redis().get_client()
        
        # Get processed events count by type
        event_counts = {}
        event_types = ["lead_scoring", "blockchain_events", "chat_analysis", "ecommerce"]
        
        for event_type in event_types:
            keys = redis_client.keys(f"processed:{event_type}:*")
            event_counts[event_type] = len(keys)
        
        # Get queue depths
        queue_depths = {}
        for event_type in event_types:
            queue_name = f"events:{event_type}"
            queue_depths[event_type] = redis_client.llen(queue_name)
        
        # Calculate total events processed today
        today = datetime.utcnow().date()
        total_today = sum(event_counts.values())
        
        return {
            "overview": {
                "total_events_processed": sum(event_counts.values()),
                "events_processed_today": total_today,
                "active_queues": len([q for q in queue_depths.values() if q > 0]),
                "total_pending": sum(queue_depths.values())
            },
            "event_counts": event_counts,
            "queue_depths": queue_depths,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get dashboard data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get dashboard data"
        )

@router.get("/leads")
async def get_lead_analytics(current_user: User = Depends(require_analyst)):
    """Get lead scoring analytics"""
    try:
        redis_client = get_redis().get_client()
        keys = redis_client.keys("processed:lead_scoring:*")
        
        leads = []
        hot_leads = 0
        warm_leads = 0
        cold_leads = 0
        
        for key in keys[-50:]:  # Get last 50
            data = redis_client.get(key)
            if data:
                try:
                    lead_data = json.loads(data)
                    leads.append(lead_data)
                    
                    # Categorize leads based on AI analysis
                    ai_analysis = lead_data.get("ai_analysis", "").lower()
                    if "hot" in ai_analysis:
                        hot_leads += 1
                    elif "warm" in ai_analysis:
                        warm_leads += 1
                    else:
                        cold_leads += 1
                        
                except json.JSONDecodeError:
                    continue
        
        return {
            "total_leads": len(leads),
            "recent_leads": leads[-10:],  # Last 10 for display
            "summary": {
                "hot_leads": hot_leads,
                "warm_leads": warm_leads,
                "cold_leads": cold_leads,
                "conversion_rate": round((hot_leads / max(len(leads), 1)) * 100, 2)
            },
            "chart_data": [
                {"name": "Hot", "value": hot_leads, "color": "#ff4444"},
                {"name": "Warm", "value": warm_leads, "color": "#ffaa00"},
                {"name": "Cold", "value": cold_leads, "color": "#4444ff"}
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get lead analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get lead analytics"
        )

@router.get("/blockchain")
async def get_blockchain_analytics(current_user: User = Depends(require_analyst)):
    """Get blockchain analytics"""
    try:
        redis_client = get_redis().get_client()
        keys = redis_client.keys("processed:blockchain_events:*")
        
        events = []
        total_volume = 0
        nft_sales = 0
        token_transfers = 0
        
        for key in keys[-50:]:  # Get last 50
            data = redis_client.get(key)
            if data:
                try:
                    event_data = json.loads(data)
                    events.append(event_data)
                    
                    # Calculate metrics
                    if "nft_sale" in str(event_data.get("sale_id", "")):
                        nft_sales += 1
                        price = event_data.get("price", 0)
                        if isinstance(price, (int, float)):
                            total_volume += price
                    elif "token_transfer" in str(event_data.get("transfer_id", "")):
                        token_transfers += 1
                        
                except json.JSONDecodeError:
                    continue
        
        avg_price = total_volume / max(nft_sales, 1)
        
        return {
            "total_events": len(events),
            "recent_events": events[-10:],
            "summary": {
                "total_volume": round(total_volume, 2),
                "nft_sales": nft_sales,
                "token_transfers": token_transfers,
                "avg_price": round(avg_price, 2)
            },
            "chart_data": [
                {"name": "NFT Sales", "value": nft_sales},
                {"name": "Token Transfers", "value": token_transfers}
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get blockchain analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get blockchain analytics"
        )

@router.get("/chat")
async def get_chat_analytics(current_user: User = Depends(require_analyst)):
    """Get chat analysis analytics"""
    try:
        redis_client = get_redis().get_client()
        keys = redis_client.keys("processed:chat_analysis:*")
        
        messages = []
        positive_sentiment = 0
        negative_sentiment = 0
        neutral_sentiment = 0
        total_engagement = 0
        
        for key in keys[-50:]:  # Get last 50
            data = redis_client.get(key)
            if data:
                try:
                    message_data = json.loads(data)
                    messages.append(message_data)
                    
                    # Analyze sentiment
                    sentiment = message_data.get("sentiment", {})
                    sentiment_label = sentiment.get("label", "neutral")
                    
                    if sentiment_label == "positive":
                        positive_sentiment += 1
                    elif sentiment_label == "negative":
                        negative_sentiment += 1
                    else:
                        neutral_sentiment += 1
                    
                    # Sum engagement scores
                    engagement = message_data.get("engagement_score", 0)
                    if isinstance(engagement, (int, float)):
                        total_engagement += engagement
                        
                except json.JSONDecodeError:
                    continue
        
        avg_engagement = total_engagement / max(len(messages), 1)
        sentiment_ratio = positive_sentiment / max(len(messages), 1)
        
        return {
            "total_messages": len(messages),
            "recent_messages": messages[-10:],
            "summary": {
                "positive_sentiment": positive_sentiment,
                "negative_sentiment": negative_sentiment,
                "neutral_sentiment": neutral_sentiment,
                "sentiment_ratio": round(sentiment_ratio, 2),
                "avg_engagement": round(avg_engagement, 2)
            },
            "chart_data": [
                {"name": "Positive", "value": positive_sentiment, "color": "#00ff00"},
                {"name": "Negative", "value": negative_sentiment, "color": "#ff0000"},
                {"name": "Neutral", "value": neutral_sentiment, "color": "#888888"}
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get chat analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get chat analytics"
        )

@router.get("/trends")
async def get_trends_data(
    days: int = 7,
    current_user: User = Depends(require_analyst)
):
    """Get trends data for the last N days"""
    try:
        # This would typically query a time-series database
        # For now, return mock trend data
        
        trend_data = []
        for i in range(days):
            date = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
            trend_data.append({
                "date": date,
                "leads": max(0, 50 - i * 5 + (i % 3) * 10),
                "blockchain": max(0, 30 - i * 2 + (i % 2) * 8),
                "chat": max(0, 100 - i * 8 + (i % 4) * 15),
                "total": max(0, 180 - i * 15 + (i % 5) * 25)
            })
        
        return {
            "trends": list(reversed(trend_data)),
            "period": f"Last {days} days"
        }
        
    except Exception as e:
        logger.error(f"Failed to get trends data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get trends data"
        )

@router.get("/graph-insights")
async def get_graph_insights(current_user: User = Depends(require_analyst)):
    """Get graph analytics insights from Neo4j"""
    try:
        neo4j_db = get_neo4j()
        
        # Example graph queries
        queries = {
            "user_event_relationships": """
                MATCH (u:User)-[r:CREATED]->(e:Event)
                RETURN u.email, count(e) as event_count
                ORDER BY event_count DESC
                LIMIT 10
            """,
            "event_type_distribution": """
                MATCH (e:Event)
                RETURN e.type, count(e) as count
                ORDER BY count DESC
            """,
            "recent_activity": """
                MATCH (e:Event)
                WHERE e.timestamp > datetime() - duration('P1D')
                RETURN count(e) as recent_events
            """
        }
        
        results = {}
        for query_name, query in queries.items():
            try:
                result = neo4j_db.execute_query(query)
                results[query_name] = [dict(record) for record in result]
            except Exception as query_error:
                logger.warning(f"Graph query {query_name} failed: {query_error}")
                results[query_name] = []
        
        return {
            "graph_insights": results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get graph insights: {e}")
        # Return empty results if Neo4j is not available
        return {
            "graph_insights": {
                "user_event_relationships": [],
                "event_type_distribution": [],
                "recent_activity": []
            },
            "timestamp": datetime.utcnow().isoformat(),
            "note": "Graph database not available"
        }