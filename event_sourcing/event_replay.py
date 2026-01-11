"""
Event Replay - Demonstrate how to replay events to rebuild state.
This is a key feature of Event Sourcing.
"""

import json
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from event_sourcing.event_store import EventStore
from event_sourcing.events import EventType


class EventReplayer:
    """
    Replays events to rebuild state.
    Demonstrates the power of Event Sourcing.
    """

    def __init__(self, db: Session):
        self.event_store = EventStore(db)

    def replay_item_state(self, item_id: int) -> Optional[Dict[str, Any]]:
        """
        Replay all events for an item to rebuild its current state.

        This demonstrates:
        1. How you can reconstruct state from events
        2. Audit trail - see every change that happened
        3. Time travel - rebuild state at any point in time

        Args:
            item_id: ID of the item

        Returns:
            Dictionary with current state and history
        """
        events = self.event_store.get_events_for_aggregate(item_id)

        if not events:
            return None

        # Initialize state
        state = {
            "current": {},
            "history": [],
            "event_count": len(events),
            "created_at": None,
            "last_modified_at": None,
        }

        # Replay each event
        for event in events:
            payload = json.loads(event.payload)

            event_info = {
                "sequence": event.sequence_number,
                "type": event.event_type,
                "timestamp": event.timestamp.isoformat(),
                "user": event.user_id,
                "changes": payload,
            }

            state["history"].append(event_info)

            # Apply event to current state
            if event.event_type == EventType.ITEM_CREATED.value:
                state["current"] = {
                    "id": item_id,
                    "name": payload["name"],
                    "description": payload["description"],
                    "category": payload["category"],
                    "image_urls": payload["image_urls"],
                    "location_lat": payload["location_lat"],
                    "location_lon": payload["location_lon"],
                    "owner_id": payload["owner_id"],
                    "status": payload["status"],
                }
                state["created_at"] = event.timestamp.isoformat()

            elif event.event_type == EventType.ITEM_UPDATED.value:
                # Apply changes
                for field, value in payload["changes"].items():
                    state["current"][field] = value
                state["last_modified_at"] = event.timestamp.isoformat()

            elif event.event_type == EventType.ITEM_STATUS_CHANGED.value:
                state["current"]["status"] = payload["new_status"]
                state["last_modified_at"] = event.timestamp.isoformat()

            elif event.event_type == EventType.ITEM_DELETED.value:
                state["current"]["status"] = "deleted"
                state["current"]["deleted_at"] = event.timestamp.isoformat()

        return state

    def replay_to_timestamp(
        self, item_id: int, target_time: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        Time travel - rebuild state as it was at a specific point in time.

        This is incredibly powerful for:
        - Debugging: "What was the state when bug occurred?"
        - Auditing: "What was the item status on Dec 1st?"
        - Compliance: Legal requirements to show historical state

        Args:
            item_id: ID of the item
            target_time: Point in time to rebuild to

        Returns:
            State as it was at target_time
        """
        events = self.event_store.get_events_for_aggregate(item_id)

        # Filter events up to target time
        events = [e for e in events if e.timestamp <= target_time]

        if not events:
            return None

        state = {}

        # Replay events up to target time
        for event in events:
            payload = json.loads(event.payload)

            if event.event_type == EventType.ITEM_CREATED.value:
                state = {
                    "id": item_id,
                    "name": payload["name"],
                    "description": payload["description"],
                    "category": payload["category"],
                    "status": payload["status"],
                    "as_of": target_time.isoformat(),
                    "event_version": event.aggregate_version,
                }

            elif event.event_type == EventType.ITEM_UPDATED.value:
                for field, value in payload["changes"].items():
                    state[field] = value

            elif event.event_type == EventType.ITEM_STATUS_CHANGED.value:
                state["status"] = payload["new_status"]

        return state

    def get_audit_trail(
        self, item_id: int, event_type: Optional[EventType] = None
    ) -> list:
        """
        Get complete audit trail for an item.

        Shows:
        - Who changed what
        - When it was changed
        - What the previous value was

        Args:
            item_id: ID of the item
            event_type: Optional filter for specific event types

        Returns:
            List of audit entries
        """
        events = self.event_store.get_events_for_aggregate(item_id)

        audit_trail = []

        for event in events:
            if event_type and event.event_type != event_type.value:
                continue

            payload = json.loads(event.payload)

            entry = {
                "sequence": event.sequence_number,
                "event_type": event.event_type,
                "timestamp": event.timestamp.isoformat(),
                "user_id": event.user_id,
                "version": event.aggregate_version,
            }

            # Add specific details based on event type
            if event.event_type == EventType.ITEM_UPDATED.value:
                entry["changes"] = payload.get("changes", {})
                entry["previous_values"] = payload.get("previous_values", {})

            elif event.event_type == EventType.ITEM_STATUS_CHANGED.value:
                entry["old_status"] = payload.get("old_status")
                entry["new_status"] = payload.get("new_status")
                entry["reason"] = payload.get("reason")

            audit_trail.append(entry)

        return audit_trail
