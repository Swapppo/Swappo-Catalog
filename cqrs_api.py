"""
CQRS API Endpoints - Demonstrates Event Sourcing + CQRS pattern.

Write endpoints (Commands) - Change state
Read endpoints (Queries) - Query state
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from event_sourcing.command_handlers import CommandHandler
from event_sourcing.commands import (
    ChangeItemStatusCommand,
    CreateItemCommand,
    UpdateItemCommand,
)
from event_sourcing.event_replay import EventReplayer
from event_sourcing.projections import rebuild_read_model_for_item
from event_sourcing.queries import QueryHandler
from models import ItemCreate, ItemResponse, ItemStatus, ItemUpdate

router = APIRouter(prefix="/api/v2", tags=["CQRS Items"])


# ==================== WRITE SIDE (Commands) ====================


@router.post("/items", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item_cqrs(
    item_data: ItemCreate,
    user_id: str = "demo-user",  # In production, get from auth token
    db: Session = Depends(get_db),
):
    """
    **COMMAND: Create Item**

    Write side - Creates an item using Event Sourcing.

    Flow:
    1. Receives CreateItemCommand
    2. Emits ItemCreatedEvent to event store
    3. Updates read model (projection)
    4. Returns created item
    """
    handler = CommandHandler(db)

    command = CreateItemCommand(
        user_id=user_id,
        name=item_data.name,
        description=item_data.description,
        category=item_data.category,
        image_urls=item_data.image_urls,
        location_lat=item_data.location_lat,
        location_lon=item_data.location_lon,
        owner_id=item_data.owner_id,
    )

    item_id = handler.handle_create_item(command)

    # Query the read model for response
    query_handler = QueryHandler(db)
    item = query_handler.get_item_by_id(item_id)

    return ItemResponse.model_validate(item)


@router.put("/items/{item_id}", response_model=ItemResponse)
async def update_item_cqrs(
    item_id: int,
    item_data: ItemUpdate,
    user_id: str = "demo-user",
    db: Session = Depends(get_db),
):
    """
    **COMMAND: Update Item**

    Write side - Updates an item using Event Sourcing.

    Emits ItemUpdatedEvent with changes and previous values for audit trail.
    """
    handler = CommandHandler(db)

    # Build changes dict from ItemUpdate
    changes = item_data.model_dump(exclude_unset=True)

    command = UpdateItemCommand(user_id=user_id, item_id=item_id, changes=changes)

    handler.handle_update_item(command)

    # Query updated item
    query_handler = QueryHandler(db)
    item = query_handler.get_item_by_id(item_id)

    return ItemResponse.model_validate(item)


@router.patch("/items/{item_id}/status")
async def change_item_status_cqrs(
    item_id: int,
    new_status: ItemStatus,
    reason: Optional[str] = None,
    user_id: str = "demo-user",
    db: Session = Depends(get_db),
):
    """
    **COMMAND: Change Item Status**

    Write side - Changes item status with full audit trail.

    Emits StatusChangedEvent showing old status, new status, and reason.
    """
    handler = CommandHandler(db)

    command = ChangeItemStatusCommand(
        user_id=user_id, item_id=item_id, new_status=new_status.value, reason=reason
    )

    handler.handle_change_status(command)

    return {
        "message": f"Item {item_id} status changed to {new_status}",
        "item_id": item_id,
        "new_status": new_status,
    }


# ==================== READ SIDE (Queries) ====================


@router.get("/items/{item_id}", response_model=ItemResponse)
async def get_item_cqrs(item_id: int, db: Session = Depends(get_db)):
    """
    **QUERY: Get Item by ID**

    Read side - Queries optimized read model.
    Does NOT touch event store.
    """
    query_handler = QueryHandler(db)
    item = query_handler.get_item_by_id(item_id)

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Item {item_id} not found"
        )

    return ItemResponse.model_validate(item)


@router.get("/items", response_model=List[ItemResponse])
async def search_items_cqrs(
    search: Optional[str] = None,
    category: Optional[str] = None,
    status: ItemStatus = ItemStatus.active,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    **QUERY: Search Items**

    Read side - Complex query against optimized read model.
    """
    query_handler = QueryHandler(db)
    items = query_handler.search_items(
        search_term=search, category=category, status=status, limit=limit, offset=offset
    )

    return [ItemResponse.model_validate(item) for item in items]


@router.get("/items/owner/{owner_id}", response_model=List[ItemResponse])
async def get_owner_items_cqrs(
    owner_id: str, status: Optional[ItemStatus] = None, db: Session = Depends(get_db)
):
    """
    **QUERY: Get Items by Owner**

    Read side query.
    """
    query_handler = QueryHandler(db)
    items = query_handler.get_items_by_owner(owner_id, status)

    return [ItemResponse.model_validate(item) for item in items]


@router.get("/stats")
async def get_statistics_cqrs(db: Session = Depends(get_db)):
    """
    **QUERY: Get Statistics**

    Read side - Aggregated statistics from read model.
    """
    query_handler = QueryHandler(db)
    return query_handler.get_item_statistics()


# ==================== EVENT SOURCING FEATURES ====================


@router.get("/items/{item_id}/history")
async def get_item_history(item_id: int, db: Session = Depends(get_db)):
    """
    **EVENT SOURCING: Get Complete History**

    Shows the power of Event Sourcing:
    - Every change that happened to this item
    - Who made the change
    - When it happened
    - What the previous values were
    """
    replayer = EventReplayer(db)
    state = replayer.replay_item_state(item_id)

    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No history found for item {item_id}",
        )

    return state


@router.get("/items/{item_id}/audit-trail")
async def get_audit_trail(item_id: int, db: Session = Depends(get_db)):
    """
    **EVENT SOURCING: Audit Trail**

    Complete audit trail showing all changes with previous values.
    Critical for compliance and debugging.
    """
    replayer = EventReplayer(db)
    audit = replayer.get_audit_trail(item_id)

    if not audit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No audit trail found for item {item_id}",
        )

    return {"item_id": item_id, "total_events": len(audit), "audit_trail": audit}


@router.post("/items/{item_id}/rebuild")
async def rebuild_item_from_events(item_id: int, db: Session = Depends(get_db)):
    """
    **EVENT REPLAY: Rebuild State from Events**

    Demonstrates event replay:
    1. Deletes current read model
    2. Replays all events from event store
    3. Rebuilds the current state

    This proves that events are the source of truth!
    """
    item = rebuild_read_model_for_item(db, item_id)

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No events found for item {item_id}",
        )

    return {
        "message": "Item successfully rebuilt from events",
        "item_id": item_id,
        "item": ItemResponse.model_validate(item),
    }


@router.get("/items/{item_id}/time-travel")
async def time_travel(
    item_id: int,
    timestamp: str,  # ISO format: "2024-01-15T10:30:00"
    db: Session = Depends(get_db),
):
    """
    **EVENT SOURCING: Time Travel**

    See what the item looked like at any point in history!

    Example: /items/5/time-travel?timestamp=2024-01-15T10:30:00
    """
    try:
        target_time = datetime.fromisoformat(timestamp)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid timestamp format. Use ISO format: 2024-01-15T10:30:00",
        )

    replayer = EventReplayer(db)
    state = replayer.replay_to_timestamp(item_id, target_time)

    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {item_id} did not exist at {timestamp}",
        )

    return {"item_id": item_id, "timestamp": timestamp, "state_at_time": state}
