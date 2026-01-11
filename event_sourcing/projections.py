"""
Projections - Update read models based on events.
This is the READ side of CQRS.
"""

from sqlalchemy.orm import Session

from event_sourcing.events import (
    DomainEvent,
    EventType,
    ItemCreatedEvent,
    ItemDeletedEvent,
    ItemStatusChangedEvent,
    ItemUpdatedEvent,
)
from models import ItemDB


def update_read_model(db: Session, event: DomainEvent) -> None:
    """
    Update the read model (ItemDB) based on events.
    This is a projection that maintains a denormalized view for queries.

    Args:
        db: Database session
        event: Domain event to process
    """

    if event.event_type == EventType.ITEM_CREATED:
        _handle_item_created(db, event)

    elif event.event_type == EventType.ITEM_UPDATED:
        _handle_item_updated(db, event)

    elif event.event_type == EventType.ITEM_STATUS_CHANGED:
        _handle_status_changed(db, event)

    elif event.event_type == EventType.ITEM_DELETED:
        _handle_item_deleted(db, event)


def _handle_item_created(db: Session, event: ItemCreatedEvent) -> None:
    """Create a new item in the read model"""
    item = ItemDB(
        id=event.aggregate_id,
        name=event.name,
        description=event.description,
        category=event.category,
        image_urls=event.image_urls,
        location_lat=event.location_lat,
        location_lon=event.location_lon,
        owner_id=event.owner_id,
        status=event.status,
        created_at=event.timestamp,
        updated_at=event.timestamp,
    )

    db.add(item)
    db.commit()


def _handle_item_updated(db: Session, event: ItemUpdatedEvent) -> None:
    """Update an item in the read model"""
    item = db.query(ItemDB).filter(ItemDB.id == event.aggregate_id).first()

    if item:
        # Apply changes
        for field, value in event.changes.items():
            if hasattr(item, field):
                setattr(item, field, value)

        item.updated_at = event.timestamp
        db.commit()


def _handle_status_changed(db: Session, event: ItemStatusChangedEvent) -> None:
    """Update item status in the read model"""
    item = db.query(ItemDB).filter(ItemDB.id == event.aggregate_id).first()

    if item:
        item.status = event.new_status
        item.updated_at = event.timestamp
        db.commit()


def _handle_item_deleted(db: Session, event: ItemDeletedEvent) -> None:
    """
    Handle item deletion.
    We don't actually delete from read model - we mark as archived.
    True deletion would lose query history.
    """
    item = db.query(ItemDB).filter(ItemDB.id == event.aggregate_id).first()

    if item:
        item.status = "archived"
        item.updated_at = event.timestamp
        db.commit()


def rebuild_read_model_for_item(db: Session, item_id: int) -> ItemDB:
    """
    Rebuild the read model for a specific item by replaying all its events.
    This demonstrates event replay capability.

    Args:
        db: Database session
        item_id: ID of item to rebuild

    Returns:
        Rebuilt item
    """
    import json

    from event_sourcing.event_store import EventStore

    event_store = EventStore(db)
    events = event_store.get_events_for_aggregate(item_id)

    if not events:
        return None

    # Delete existing read model entry
    db.query(ItemDB).filter(ItemDB.id == item_id).delete()

    # Replay all events
    for event_entry in events:
        payload = json.loads(event_entry.payload)

        # Reconstruct event object based on type
        if event_entry.event_type == EventType.ITEM_CREATED.value:
            event = ItemCreatedEvent(
                aggregate_id=event_entry.aggregate_id,
                user_id=event_entry.user_id,
                timestamp=event_entry.timestamp,
                **payload
            )
            update_read_model(db, event)

        elif event_entry.event_type == EventType.ITEM_UPDATED.value:
            event = ItemUpdatedEvent(
                aggregate_id=event_entry.aggregate_id,
                user_id=event_entry.user_id,
                timestamp=event_entry.timestamp,
                **payload
            )
            update_read_model(db, event)

        elif event_entry.event_type == EventType.ITEM_STATUS_CHANGED.value:
            event = ItemStatusChangedEvent(
                aggregate_id=event_entry.aggregate_id,
                user_id=event_entry.user_id,
                timestamp=event_entry.timestamp,
                **payload
            )
            update_read_model(db, event)

        elif event_entry.event_type == EventType.ITEM_DELETED.value:
            event = ItemDeletedEvent(
                aggregate_id=event_entry.aggregate_id,
                user_id=event_entry.user_id,
                timestamp=event_entry.timestamp,
                **payload
            )
            update_read_model(db, event)

    # Return rebuilt item
    return db.query(ItemDB).filter(ItemDB.id == item_id).first()
