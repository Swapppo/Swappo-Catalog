# Event Sourcing + CQRS Implementation

Complete implementation of **Event Sourcing** and **CQRS** patterns for the Swappo Catalog service.

## 🎯 What This Implements

### ✅ Minimalne zahteve (Requirements)

1. **Event Sourcing za sledenje sprememb podatkov** ✅
   - All data changes stored as immutable events
   - Complete audit trail of all modifications
   - Events stored in `event_store` table

2. **CQRS za ločene modele branja in pisanja** ✅
   - **Write side**: Commands → Events → Event Store
   - **Read side**: Queries → Optimized read models
   - Separate API endpoints for reads and writes

3. **Ponovno predvajanje dogodkov za obnovo stanja** ✅
   - Event replay capability implemented
   - Can rebuild state from events at any time
   - Time travel feature to view historical state

---

## 🚀 Quick Start

### 1. Install Dependencies

No additional dependencies needed! Uses existing FastAPI, SQLAlchemy, and PostgreSQL.

### 2. Run Database Migration

Create the event_store table:

```bash
cd Swappo-Catalog
python migrate_event_store.py
```

### 3. Start the Service

```bash
python main.py
```

The service will start on `http://localhost:8001`

### 4. Run the Demo

```bash
python demo_event_sourcing.py
```

This will demonstrate all Event Sourcing + CQRS features!

---

## 📚 Documentation

See [EVENT_SOURCING_CQRS_GUIDE.md](../guides/EVENT_SOURCING_CQRS_GUIDE.md) for:
- Detailed architecture explanation
- How Event Sourcing works
- How CQRS works
- API documentation
- Testing guide
- Deployment instructions

---

## 🏗️ Architecture Overview

```
WRITE SIDE                EVENT STORE              READ SIDE
───────────              ─────────────             ──────────
Commands                 Append-Only Log           Queries
   ↓                            ↓                      ↓
Handlers    →  Events  →  event_store  →  Projections  →  items
   ↓                            ↓                      ↓
Validate                   Source of Truth        Fast Reads
```

---

## 🔧 API Endpoints

### Write (Commands)

- `POST /api/v2/items` - Create item
- `PUT /api/v2/items/{id}` - Update item
- `PATCH /api/v2/items/{id}/status` - Change status

### Read (Queries)

- `GET /api/v2/items/{id}` - Get item
- `GET /api/v2/items` - Search items
- `GET /api/v2/items/owner/{owner_id}` - Get by owner

### Event Sourcing Features

- `GET /api/v2/items/{id}/history` - Complete event history
- `GET /api/v2/items/{id}/audit-trail` - Audit trail
- `POST /api/v2/items/{id}/rebuild` - Rebuild from events
- `GET /api/v2/items/{id}/time-travel?timestamp=...` - Time travel

---

## 📁 File Structure

```
event_sourcing/
├── events.py              # Domain events (ItemCreated, ItemUpdated, etc.)
├── event_store.py         # Event persistence layer
├── commands.py            # Command definitions
├── command_handlers.py    # Process commands, emit events
├── queries.py             # Query handlers (read side)
├── projections.py         # Update read models from events
└── event_replay.py        # Replay events for debugging/audit

cqrs_api.py               # CQRS REST API endpoints
demo_event_sourcing.py    # Demo script
migrate_event_store.py    # Database migration
```

---

## 🧪 Example Usage

### Create Item (Command)

```bash
curl -X POST http://localhost:8001/api/v2/items \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Vintage Camera",
    "description": "Classic 35mm camera",
    "category": "electronics",
    "image_urls": ["http://example.com/camera.jpg"],
    "location_lat": 46.0569,
    "location_lon": 14.5058,
    "owner_id": "user123"
  }'
```

### Get Complete History

```bash
curl http://localhost:8001/api/v2/items/1/history
```

Returns:
```json
{
  "current": {
    "id": 1,
    "name": "Vintage Camera",
    "status": "active"
  },
  "history": [
    {
      "sequence": 1,
      "type": "item_created",
      "timestamp": "2024-01-15T10:00:00Z",
      "user": "demo-user",
      "changes": {...}
    }
  ],
  "event_count": 1
}
```

### Rebuild from Events

```bash
curl -X POST http://localhost:8001/api/v2/items/1/rebuild
```

This demonstrates that events are the source of truth!

---

## 💾 Database Schema

### event_store (New)

```sql
CREATE TABLE event_store (
    sequence_number SERIAL PRIMARY KEY,
    event_id VARCHAR(36) UNIQUE NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    aggregate_id INTEGER NOT NULL,
    aggregate_type VARCHAR(50) NOT NULL,
    aggregate_version INTEGER NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    payload TEXT NOT NULL,
    metadata TEXT DEFAULT '{}'
);
```

### items (Existing - Read Model)

Your existing `items` table serves as the optimized read model (projection).

---

## 🎓 Key Concepts

### Event Sourcing

**Instead of:**
```sql
UPDATE items SET status = 'swapped' WHERE id = 1
```

**We store:**
```sql
INSERT INTO event_store (event_type, payload) VALUES
  ('item_status_changed', '{"old": "active", "new": "swapped"}')
```

**Benefits:**
- ✅ Complete audit trail
- ✅ Can rebuild state anytime
- ✅ Time travel capability
- ✅ Never lose data

### CQRS

**Separate models for:**
- **Writing** (Commands) - Business logic, validation
- **Reading** (Queries) - Optimized for fast queries

**Benefits:**
- ✅ Independent scaling
- ✅ Optimized performance
- ✅ Clear separation of concerns

---

## 🚢 Deployment

### Local Development

```bash
# 1. Run migration
python migrate_event_store.py

# 2. Start service
python main.py

# 3. Test
python demo_event_sourcing.py
```

### GKE Deployment

1. **Run migration on Cloud SQL:**
   ```bash
   kubectl run -it --rm psql --image=postgres:15 --restart=Never -- \
     psql -h <CLOUD_SQL_IP> -U swappo_user -d swappo_catalog \
     -c "$(cat migrate_event_store.py)"
   ```

2. **Deploy service:**
   ```bash
   kubectl apply -f k8s-gke/catalog-service.yaml
   ```

3. **Verify:**
   ```bash
   kubectl logs -n swappo -l app=catalog-service
   ```

---

## 📊 Monitoring

Key metrics to track:

- `events_stored_total` - Total events stored
- `event_replay_duration_seconds` - Time to replay events
- `read_model_lag_seconds` - Delay between event and projection update

---

## ✅ Testing the Requirements

### 1. Event Sourcing za sledenje sprememb

```bash
# Create and modify an item
curl -X POST http://localhost:8001/api/v2/items ...
curl -X PUT http://localhost:8001/api/v2/items/1 ...

# View all changes
curl http://localhost:8001/api/v2/items/1/history
```

✅ All changes are tracked as events!

### 2. CQRS ločeni modeli

```bash
# Write: Uses CommandHandler → Event Store
curl -X POST http://localhost:8001/api/v2/items ...

# Read: Uses QueryHandler → Read Model
curl http://localhost:8001/api/v2/items/1
```

✅ Separate write and read models!

### 3. Ponovno predvajanje dogodkov

```bash
# Rebuild state from events
curl -X POST http://localhost:8001/api/v2/items/1/rebuild
```

✅ Events can be replayed to restore state!

---

## 🎉 Success Criteria

All requirements met:

- ✅ **Event Sourcing** implemented with complete audit trail
- ✅ **CQRS** with separate command and query models
- ✅ **Event replay** capability demonstrated
- ✅ **Time travel** feature for historical state
- ✅ **Full API** with documentation
- ✅ **Demo script** showing all features
- ✅ **Ready for GKE deployment**

---

## 📖 Further Reading

- [Complete Guide](../guides/EVENT_SOURCING_CQRS_GUIDE.md)
- [Event Sourcing Pattern](https://martinfowler.com/eaaDev/EventSourcing.html)
- [CQRS Pattern](https://martinfowler.com/bliki/CQRS.html)

---

## 🤝 Contributing

To extend this implementation:

1. Add new event types in `event_sourcing/events.py`
2. Add command handlers in `event_sourcing/command_handlers.py`
3. Update projections in `event_sourcing/projections.py`
4. Add API endpoints in `cqrs_api.py`

---

**Built with ❤️ for Swappo**
