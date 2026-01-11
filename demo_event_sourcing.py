"""
Demo script to showcase Event Sourcing + CQRS implementation.

This script demonstrates:
1. Creating items (Commands)
2. Updating items with full audit trail
3. Viewing event history
4. Event replay to rebuild state
5. Time travel to see historical state
"""

import json
import time

import requests

BASE_URL = "http://localhost:8001/api/v2"


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_json(data):
    """Pretty print JSON data"""
    print(json.dumps(data, indent=2))


def demo_event_sourcing_cqrs():
    """Run the complete demo"""

    print_section("🚀 Event Sourcing + CQRS Demo")
    print("This demo shows how Event Sourcing and CQRS work in practice.\n")

    # Step 1: Create an item (COMMAND)
    print_section("Step 1: CREATE ITEM (Command)")
    print("Sending CreateItemCommand...")

    create_payload = {
        "name": "Vintage Camera",
        "description": "Classic 35mm film camera in excellent condition",
        "category": "electronics",
        "image_urls": ["https://example.com/camera.jpg"],
        "location_lat": 46.0569,
        "location_lon": 14.5058,
        "owner_id": "demo-user-123",
    }

    response = requests.post(f"{BASE_URL}/items", json=create_payload)
    item = response.json()
    item_id = item["id"]

    print(f"✅ Item created with ID: {item_id}")
    print(f"   Name: {item['name']}")
    print(f"   Status: {item['status']}")

    time.sleep(1)  # Small delay for timestamp differences

    # Step 2: Update item (COMMAND)
    print_section("Step 2: UPDATE ITEM (Command)")
    print("Sending UpdateItemCommand to change description...")

    update_payload = {
        "description": "Classic 35mm film camera - includes leather case and extra lens!"
    }

    response = requests.put(f"{BASE_URL}/items/{item_id}", json=update_payload)
    print("✅ Item updated successfully")

    time.sleep(1)

    # Step 3: Change status (COMMAND)
    print_section("Step 3: CHANGE STATUS (Command)")
    print("Sending ChangeStatusCommand...")

    response = requests.patch(
        f"{BASE_URL}/items/{item_id}/status",
        params={
            "new_status": "swapped",
            "reason": "Successfully traded with user456 for a vinyl record player",
        },
    )

    print("✅ Status changed to 'swapped'")

    # Step 4: Query item (QUERY)
    print_section("Step 4: GET ITEM (Query)")
    print("Querying read model...")

    response = requests.get(f"{BASE_URL}/items/{item_id}")
    current_item = response.json()

    print("Current state from read model:")
    print_json(
        {
            "id": current_item["id"],
            "name": current_item["name"],
            "description": current_item["description"],
            "status": current_item["status"],
        }
    )

    # Step 5: View complete history
    print_section("Step 5: EVENT HISTORY (Event Sourcing)")
    print("Fetching complete event history from event store...")

    response = requests.get(f"{BASE_URL}/items/{item_id}/history")
    history = response.json()

    print(f"Total events: {history['event_count']}")
    print("\nEvent Timeline:")

    for event in history["history"]:
        print(f"\n  [{event['sequence']}] {event['type']}")
        print(f"      Time: {event['timestamp']}")
        print(f"      User: {event['user']}")
        if event["type"] == "item_updated":
            print(f"      Changes: {event['changes']}")
        elif event["type"] == "item_status_changed":
            print(
                f"      Old: {event['changes']['old_status']} → New: {event['changes']['new_status']}"
            )

    # Step 6: Audit trail
    print_section("Step 6: AUDIT TRAIL")
    print("Getting detailed audit trail with previous values...")

    response = requests.get(f"{BASE_URL}/items/{item_id}/audit-trail")
    audit = response.json()

    print(f"Total audit entries: {audit['total_events']}")
    print("\nAudit Trail:")

    for entry in audit["audit_trail"]:
        print(f"\n  Event #{entry['sequence']}: {entry['event_type']}")
        print(f"    Timestamp: {entry['timestamp']}")
        print(f"    User: {entry['user_id']}")

        if "changes" in entry:
            print(f"    Changes: {entry['changes']}")
        if "previous_values" in entry:
            print(f"    Previous: {entry['previous_values']}")
        if "old_status" in entry:
            print(f"    Status: {entry['old_status']} → {entry['new_status']}")
            if entry.get("reason"):
                print(f"    Reason: {entry['reason']}")

    # Step 7: Event Replay
    print_section("Step 7: EVENT REPLAY")
    print("Demonstrating event replay to rebuild state...")
    print("This proves that events are the source of truth!")

    response = requests.post(f"{BASE_URL}/items/{item_id}/rebuild")
    rebuild_result = response.json()

    print(f"✅ {rebuild_result['message']}")
    print("\nRebuilt state:")
    rebuilt_item = rebuild_result["item"]
    print_json(
        {
            "id": rebuilt_item["id"],
            "name": rebuilt_item["name"],
            "description": rebuilt_item["description"],
            "status": rebuilt_item["status"],
        }
    )

    # Step 8: Time Travel
    print_section("Step 8: TIME TRAVEL")
    print("View historical state at a specific point in time...")

    # Get timestamp from first event
    first_event_time = history["history"][1]["timestamp"]  # After update

    print(f"Looking at state at: {first_event_time}")

    response = requests.get(
        f"{BASE_URL}/items/{item_id}/time-travel",
        params={"timestamp": first_event_time},
    )
    past_state = response.json()

    print("\nState at that time:")
    print_json(past_state["state_at_time"])

    # Summary
    print_section("📊 SUMMARY")
    print(
        """
What we demonstrated:

✅ WRITE SIDE (CQRS Commands):
   - CreateItemCommand → ItemCreatedEvent
   - UpdateItemCommand → ItemUpdatedEvent
   - ChangeStatusCommand → StatusChangedEvent

✅ READ SIDE (CQRS Queries):
   - Fast queries from optimized read model
   - No impact on event store

✅ EVENT SOURCING FEATURES:
   - Complete event history
   - Full audit trail with previous values
   - Event replay to rebuild state
   - Time travel to see historical state

✅ BENEFITS ACHIEVED:
   - Every change is tracked
   - Can't lose data - events are immutable
   - Complete compliance/audit trail
   - Can debug by seeing exact history
   - State can be rebuilt at any time
    """
    )

    print("\n" + "=" * 80)
    print("  Demo Complete! 🎉")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    try:
        demo_event_sourcing_cqrs()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to API")
        print("   Make sure the Catalog service is running on http://localhost:8001")
        print("\n   Start it with: cd Swappo-Catalog && python main.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
