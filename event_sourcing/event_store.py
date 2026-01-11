"""
Event Store - Append-only storage for domain events.
This is the source of truth for your system.
"""

import json
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Session

from event_sourcing.events import DomainEvent, EventType
from models import Base


class EventStoreEntry(Base):
    """
    Database table for storing events.
    This is an append-only log - events are NEVER updated or deleted.
    """

    __tablename__ = "event_store"

    # Primary key - auto-incrementing sequence number
    sequence_number = Column(Integer, primary_key=True, autoincrement=True)

    # Event identification
    event_id = Column(String(36), unique=True, nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)

    # Aggregate information (which item this event belongs to)
    aggregate_id = Column(Integer, nullable=False, index=True)
    aggregate_type = Column(String(50), nullable=False)
    aggregate_version = Column(Integer, nullable=False)

    # Event metadata
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    user_id = Column(String(100), nullable=False)

    # Event payload - stored as JSON
    payload = Column(Text, nullable=False)
    event_metadata = Column(Text, default="{}")

    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_aggregate", "aggregate_id", "aggregate_type"),
        Index("idx_event_type_timestamp", "event_type", "timestamp"),
    )


class EventStore:
    """
    Event Store manages persisting and retrieving events.
    """

    def __init__(self, db: Session):
        self.db = db

    def append_event(self, event: DomainEvent) -> int:
        """
        Append a new event to the event store.

        Args:
            event: Domain event to store

        Returns:
            sequence_number: The sequence number of the stored event
        """
        # Convert event to dict, excluding the base fields
        event_dict = event.model_dump()

        # Extract base fields
        base_fields = {
            "event_id",
            "event_type",
            "aggregate_id",
            "aggregate_type",
            "timestamp",
            "version",
            "user_id",
            "metadata",
        }

        # Payload is everything except base fields
        payload = {k: v for k, v in event_dict.items() if k not in base_fields}

        entry = EventStoreEntry(
            event_id=event.event_id,
            event_type=event.event_type.value,
            aggregate_id=event.aggregate_id,
            aggregate_type=event.aggregate_type,
            aggregate_version=event.version,
            timestamp=event.timestamp,
            user_id=event.user_id,
            payload=json.dumps(payload, default=str),
            event_metadata=json.dumps(event.metadata, default=str),
        )

        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)

        return entry.sequence_number

    def get_events_for_aggregate(
        self, aggregate_id: int, aggregate_type: str = "Item"
    ) -> List[EventStoreEntry]:
        """
        Get all events for a specific aggregate (e.g., all events for item #5).
        This is used for event replay and rebuilding state.

        Args:
            aggregate_id: ID of the aggregate
            aggregate_type: Type of aggregate

        Returns:
            List of events in chronological order
        """
        return (
            self.db.query(EventStoreEntry)
            .filter(
                EventStoreEntry.aggregate_id == aggregate_id,
                EventStoreEntry.aggregate_type == aggregate_type,
            )
            .order_by(EventStoreEntry.sequence_number)
            .all()
        )

    def get_events_by_type(
        self, event_type: EventType, since: Optional[datetime] = None, limit: int = 1000
    ) -> List[EventStoreEntry]:
        """
        Get events by type, optionally since a certain time.
        Useful for projections and event handlers.

        Args:
            event_type: Type of events to retrieve
            since: Optional timestamp to get events after
            limit: Maximum number of events to return

        Returns:
            List of events
        """
        query = self.db.query(EventStoreEntry).filter(
            EventStoreEntry.event_type == event_type.value
        )

        if since:
            query = query.filter(EventStoreEntry.timestamp > since)

        return query.order_by(EventStoreEntry.sequence_number).limit(limit).all()

    def get_all_events(
        self, since_sequence: Optional[int] = None, limit: int = 1000
    ) -> List[EventStoreEntry]:
        """
        Get all events, optionally since a sequence number.
        Used for rebuilding read models from scratch.

        Args:
            since_sequence: Optional sequence number to start from
            limit: Maximum number of events

        Returns:
            List of events in sequence order
        """
        query = self.db.query(EventStoreEntry)

        if since_sequence:
            query = query.filter(EventStoreEntry.sequence_number > since_sequence)

        return query.order_by(EventStoreEntry.sequence_number).limit(limit).all()

    def replay_events(
        self, aggregate_id: int, event_handler, aggregate_type: str = "Item"
    ) -> Any:
        """
        Replay all events for an aggregate to rebuild its state.
        This demonstrates how you can reconstruct state from events.

        Args:
            aggregate_id: ID of the aggregate
            event_handler: Function that processes events and builds state
            aggregate_type: Type of aggregate

        Returns:
            Reconstructed state
        """
        events = self.get_events_for_aggregate(aggregate_id, aggregate_type)

        state = None
        for event_entry in events:
            payload = json.loads(event_entry.payload)
            state = event_handler(state, event_entry.event_type, payload)

        return state
