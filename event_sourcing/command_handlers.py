"""
Command Handlers - Process commands and emit events.
This is the WRITE side of CQRS.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from event_sourcing.commands import (
    ChangeItemStatusCommand,
    CreateItemCommand,
    DeleteItemCommand,
    UpdateItemCommand,
)
from event_sourcing.event_store import EventStore
from event_sourcing.events import (
    ItemCreatedEvent,
    ItemDeletedEvent,
    ItemStatusChangedEvent,
    ItemUpdatedEvent,
)
from event_sourcing.projections import update_read_model
from models import ItemDB


class CommandHandler:
    """
    Handles commands and coordinates event creation and projection updates.
    """

    def __init__(self, db: Session):
        self.db = db
        self.event_store = EventStore(db)

    def handle_create_item(self, command: CreateItemCommand) -> int:
        """
        Handle CreateItemCommand

        Flow:
        1. Validate command
        2. Create event
        3. Store event in event store
        4. Update read model (projection)

        Returns:
            item_id: ID of created item
        """
        # Create event
        # For new items, we need to generate an ID first
        # We'll use a sequence or let the projection handle it

        # Get next item ID (simple approach - you might use UUID instead)
        last_item = self.db.query(ItemDB).order_by(ItemDB.id.desc()).first()
        next_id = (last_item.id + 1) if last_item else 1

        event = ItemCreatedEvent(
            aggregate_id=next_id,
            user_id=command.user_id,
            name=command.name,
            description=command.description,
            category=command.category,
            image_urls=command.image_urls,
            location_lat=command.location_lat,
            location_lon=command.location_lon,
            owner_id=command.owner_id,
            status="active",
        )

        # Store event
        self.event_store.append_event(event)

        # Log event
        self._log_event(event)

        # Update read model
        update_read_model(self.db, event)

        return next_id

    def handle_update_item(self, command: UpdateItemCommand) -> None:
        """
        Handle UpdateItemCommand

        Validates that item exists and creates update event.
        """
        # Get current item state from read model
        item = self.db.query(ItemDB).filter(ItemDB.id == command.item_id).first()

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item {command.item_id} not found",
            )

        # Build previous values for audit
        previous_values = {}
        for field in command.changes.keys():
            if hasattr(item, field):
                previous_values[field] = getattr(item, field)

        # Create event
        event = ItemUpdatedEvent(
            aggregate_id=command.item_id,
            user_id=command.user_id,
            changes=command.changes,
            previous_values=previous_values,
            version=self._get_next_version(command.item_id),
        )

        # Store event
        self.event_store.append_event(event)

        # Log event
        self._log_event(event)

        # Update read model
        update_read_model(self.db, event)

    def handle_change_status(self, command: ChangeItemStatusCommand) -> None:
        """
        Handle ChangeItemStatusCommand
        """
        # Get current item
        item = self.db.query(ItemDB).filter(ItemDB.id == command.item_id).first()

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item {command.item_id} not found",
            )

        # Create event
        event = ItemStatusChangedEvent(
            aggregate_id=command.item_id,
            user_id=command.user_id,
            old_status=item.status,
            new_status=command.new_status,
            reason=command.reason,
            version=self._get_next_version(command.item_id),
        )

        # Store event
        self.event_store.append_event(event)

        # Log event
        self._log_event(event)

        # Update read model
        update_read_model(self.db, event)

    def handle_delete_item(self, command: DeleteItemCommand) -> None:
        """
        Handle DeleteItemCommand
        """
        # Verify item exists
        item = self.db.query(ItemDB).filter(ItemDB.id == command.item_id).first()

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item {command.item_id} not found",
            )

        # Create event
        event = ItemDeletedEvent(
            aggregate_id=command.item_id,
            user_id=command.user_id,
            reason=command.reason,
            version=self._get_next_version(command.item_id),
        )

        # Store event
        self.event_store.append_event(event)

        # Log event
        self._log_event(event)

        # Update read model
        update_read_model(self.db, event)

    def _get_next_version(self, aggregate_id: int) -> int:
        """Get next version number for an aggregate"""
        events = self.event_store.get_events_for_aggregate(aggregate_id)
        return len(events) + 1

    def _log_event(self, event):
        """
        Log the event details to stdout (Cloud Logging)
        """
        import json
        from datetime import datetime

        # Convert event to dict for logging
        try:
            event_dict = event.model_dump()

            # Extract core fields
            event_type = getattr(event, "event_type", "unknown")
            aggregate_id = getattr(event, "aggregate_id", "unknown")
            timestamp = getattr(event, "timestamp", datetime.now())
            user_id = getattr(event, "user_id", "unknown")
            version = getattr(event, "version", 1)

            # Everything else is payload
            payload = {
                k: v
                for k, v in event_dict.items()
                if k
                not in ["event_type", "aggregate_id", "timestamp", "user_id", "version"]
            }

            print("\n🔍 --- EVENT SOURCING LOG ---")
            print(f"[{timestamp}] {event_type} (ID: {aggregate_id})")
            print(f"  User: {user_id}")
            print(f"  Version: {version}")
            print(f"  Payload: {json.dumps(payload, indent=2, default=str)}")
            print("--------------------------------------------------\n")

        except Exception as e:
            print(f"⚠️ Error logging event: {e}")
