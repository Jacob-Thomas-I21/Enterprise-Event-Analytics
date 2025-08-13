"""
Events API routes for event ingestion and management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import json
import logging

from core.database import get_db, get_redis
from core.auth import get_current_user, require_analyst
from models.user import User
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)

# Pydantic models
class EventData(BaseModel):
    event_type: str
    data: dict
    metadata: Optional[dict] = None
    timestamp: Optional[str] = None

class EventResponse(BaseModel):
    status: str
    event_id: str
    queue: str
    estimated_processing_time: str

@router.post("/ingest", response_model=EventResponse)
async def ingest_event(
    event: EventData,
    current_user: User = Depends(require_analyst)
):
    """Universal event ingestion endpoint"""
    try:
        # Add timestamp if not provided
        if not event.timestamp:
            event.timestamp = datetime.utcnow().isoformat()
        
        # Add user context
        event_payload = event.dict()
        event_payload["user_id"] = current_user.id
        event_payload["user_email"] = current_user.email
        
        # Add to queue for processing
        queue_name = f"events:{event.event_type}"
        redis_client = get_redis().get_client()
        
        redis_client.lpush(queue_name, json.dumps(event_payload))
        
        event_id = f"{event.event_type}_{int(datetime.utcnow().timestamp())}"
        
        logger.info(f"Event ingested: {event_id} by user {current_user.email}")
        
        return EventResponse(
            status="queued",
            event_id=event_id,
            queue=queue_name,
            estimated_processing_time="30s"
        )
        
    except Exception as e:
        logger.error(f"Event ingestion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest event"
        )

@router.get("/types")
async def get_event_types(current_user: User = Depends(require_analyst)):
    """Get available event types"""
    return {
        "event_types": [
            "lead_scoring",
            "blockchain_events", 
            "chat_analysis",
            "ecommerce",
            "iot_sensor",
            "social_media",
            "financial_transaction",
            "api_usage",
            "user_behavior",
            "email_campaign",
            "content_performance",
            "game_analytics",
            "supply_chain",
            "security_event",
            "health_data"
        ]
    }

@router.get("/queue-status")
async def get_queue_status(current_user: User = Depends(require_analyst)):
    """Get queue status for all event types"""
    try:
        redis_client = get_redis().get_client()
        queue_status = {}
        
        event_types = [
            "lead_scoring", "blockchain_events", "chat_analysis",
            "ecommerce", "iot_sensor", "social_media"
        ]
        
        for event_type in event_types:
            queue_name = f"events:{event_type}"
            queue_length = redis_client.llen(queue_name)
            queue_status[event_type] = {
                "queue_name": queue_name,
                "pending_events": queue_length
            }
        
        return {"queue_status": queue_status}
        
    except Exception as e:
        logger.error(f"Failed to get queue status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get queue status"
        )

@router.get("/recent")
async def get_recent_events(
    limit: int = 10,
    event_type: Optional[str] = None,
    current_user: User = Depends(require_analyst)
):
    """Get recent processed events"""
    try:
        redis_client = get_redis().get_client()
        
        if event_type:
            keys = redis_client.keys(f"processed:{event_type}:*")
        else:
            keys = redis_client.keys("processed:*")
        
        # Sort by timestamp and get recent ones
        keys = sorted(keys, reverse=True)[:limit]
        
        events = []
        for key in keys:
            data = redis_client.get(key)
            if data:
                try:
                    event_data = json.loads(data)
                    events.append(event_data)
                except json.JSONDecodeError:
                    continue
        
        return {
            "events": events,
            "total": len(events)
        }
        
    except Exception as e:
        logger.error(f"Failed to get recent events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get recent events"
        )