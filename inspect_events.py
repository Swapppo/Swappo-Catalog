import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import DATABASE_URL
from event_sourcing.event_store import EventStoreEntry

# Import your models and event store
from models import ItemDB

# Setup DB connection
# Ensure we use the correct database URL
if not DATABASE_URL:
    print("❌ DATABASE_URL environment variable not set")
    exit(1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def print_event(event):
    """Pretty print an event"""
    payload = json.loads(event.payload)
    print(f"[{event.timestamp}] {event.event_type} (Seq: {event.sequence_number})")
    print(f"  User: {event.user_id}")
    print(f"  Version: {event.aggregate_version}")
    print(f"  Payload: {json.dumps(payload, indent=2)}")
    print("-" * 50)


def inspect_recent_events():
    db = SessionLocal()
    try:
        print("\n🔍 --- RECENT EVENTS IN EVENT STORE ---")

        # Get last 10 events
        events = (
            db.query(EventStoreEntry)
            .order_by(EventStoreEntry.sequence_number.desc())
            .limit(10)
            .all()
        )

        if not events:
            print("No events found in the event store.")
            return

        for event in reversed(events):  # Show in chronological order
            print_event(event)

        print(f"\n✅ Total events found: {len(events)}")

    finally:
        db.close()


def inspect_item_history(item_id):
    db = SessionLocal()
    try:
        print(f"\n🔍 --- HISTORY FOR ITEM {item_id} ---")

        # Check if item exists in current state
        item = db.query(ItemDB).filter(ItemDB.id == item_id).first()
        if item:
            print(f"Current State: {item.name} (Status: {item.status})")
        else:
            print("Item not found in current state (might be deleted)")

        # Get events
        events = (
            db.query(EventStoreEntry)
            .filter(
                EventStoreEntry.aggregate_id == item_id,
                EventStoreEntry.aggregate_type == "Item",
            )
            .order_by(EventStoreEntry.sequence_number)
            .all()
        )

        if not events:
            print(f"No events found for item {item_id}")
            return

        for event in events:
            print_event(event)

    finally:
        db.close()


if __name__ == "__main__":
    # 1. Show the most recent events (global)
    inspect_recent_events()

    # 2. Optionally, ask for a specific item ID to inspect
    # item_id = input("\nEnter Item ID to inspect history (or press Enter to skip): ")
    # if item_id:
    #     inspect_item_history(int(item_id))
