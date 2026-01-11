# Swappo-Catalog

Item catalog microservice for the Swappo platform with CRUD operations, smart matching feed, and multi-protocol support (REST, GraphQL, gRPC).

## Features

- **CRUD Operations**: Full item listing management with soft delete
- **Smart Feed API**: Location-based filtering with Haversine distance calculation
- **Multi-Protocol Support**: REST, GraphQL, and gRPC endpoints
- **Event Sourcing/CQRS**: Event-driven architecture support
- **Image Upload**: Google Cloud Storage integration with local fallback
- **Prometheus Metrics**: Built-in monitoring and instrumentation
- **Owner Verification**: Secure ownership checks for modifications

## Quick Start

### Docker (Recommended)

```bash
docker-compose up -d
```

Optional database management UI:
```bash
docker-compose --profile tools up -d
```
Access PgAdmin at http://localhost:5050 (admin@swappo.com / admin)

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
uvicorn main:app --reload
```

## API Endpoints

### REST API

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/` | Service info | No |
| GET | `/health` | Health check | No |
| POST | `/upload-image` | Upload item image | No |
| POST | `/items` | Create item listing | No |
| GET | `/items/feed` | Get swiping feed (core matching) | No |
| GET | `/items/my-items` | Get user's items | No |
| GET | `/items/{item_id}` | Get item by ID | No |
| PUT | `/items/{item_id}` | Update item (owner only) | Yes |
| DELETE | `/items/{item_id}` | Archive item (owner only) | Yes |
| GET | `/metrics` | Prometheus metrics | No |

### GraphQL

- **Endpoint**: `/graphql`

### gRPC

- **Port**: 50051
- **Proto**: See [protos/](protos/) directory
- Generate stubs: `.\generate_grpc.ps1` (Windows) or `./generate_grpc.sh` (Linux/Mac)

### Event Sourcing/CQRS

See [EVENT_SOURCING_README.md](EVENT_SOURCING_README.md) for event-driven endpoints.

## Feed API Details

The `/items/feed` endpoint is the core matching API with advanced filtering:

**Query Parameters:**
- `user_id` (required): User requesting feed
- `limit`: Items to return (1-100, default 20)
- `exclude_item_ids`: Comma-separated IDs to exclude
- `category`: Filter by category
- `distance`: Max distance in km (requires user location)
- `user_lat`, `user_lon`: User coordinates for distance filtering

**Features:**
- Excludes user's own items
- Excludes already swiped items
- Location-based filtering (Haversine formula)
- Randomized order for discovery

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | - | PostgreSQL connection string |
| `SQL_ECHO` | false | Enable SQL query logging |
| `USE_GCS` | true | Use Google Cloud Storage for images |
| `GCS_BUCKET_NAME` | - | GCS bucket name |
| `GOOGLE_APPLICATION_CREDENTIALS` | - | Path to GCS credentials JSON |

## Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **GraphQL Playground**: http://localhost:8000/graphql

## Additional Features

- **GraphQL**: See [GRAPHQL_GUIDE.md](GRAPHQL_GUIDE.md)
- **Event Sourcing**: See [EVENT_SOURCING_README.md](EVENT_SOURCING_README.md)

## Testing

```bash
pytest
```

## Generate API Schema

```bash
python -c "import json; from main import app; print(json.dumps(app.openapi(), indent=2))" > api_schema.json
```

[Your License Here]

## Contributing

[Your Contributing Guidelines Here]

## Support

For issues and questions, please open an issue on GitHub.
