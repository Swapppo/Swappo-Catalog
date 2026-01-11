"""
Event definitions for Event Sourcing.
All events are immutable records of things that have happened.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of domain events"""

    ITEM_CREATED = "item_created"
    ITEM_UPDATED = "item_updated"
    ITEM_STATUS_CHANGED = "item_status_changed"
    ITEM_DELETED = "item_deleted"


class DomainEvent(BaseModel):
    """Base class for all domain events"""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    aggregate_id: int  # The item ID
    aggregate_type: str = "Item"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1
    user_id: str  # Who triggered the event
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ItemCreatedEvent(DomainEvent):
    """Event fired when a new item is created"""

    event_type: EventType = EventType.ITEM_CREATED

    # Event payload
    name: str
    description: str
    category: str
    image_urls: List[str]
    location_lat: float
    location_lon: float
    owner_id: str
    status: str = "active"


class ItemUpdatedEvent(DomainEvent):
    """Event fired when an item is updated"""

    event_type: EventType = EventType.ITEM_UPDATED

    # Track what changed
    changes: Dict[str, Any]  # {"name": "New Name", "description": "New Desc"}
    previous_values: Dict[str, Any]  # For audit trail


class ItemStatusChangedEvent(DomainEvent):
    """Event fired when item status changes"""

    event_type: EventType = EventType.ITEM_STATUS_CHANGED

    old_status: str
    new_status: str
    reason: Optional[str] = None  # Why status changed


class ItemDeletedEvent(DomainEvent):
    """Event fired when an item is soft-deleted"""

    event_type: EventType = EventType.ITEM_DELETED

    reason: Optional[str] = None
