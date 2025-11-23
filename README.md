# Swappo Catalog Microservice

A FastAPI-based microservice for managing item listings in the Swappo app - a Tinder-like platform for item swapping.

## Features

- **CRUD Operations**: Create, read, update, and delete item listings
- **Smart Feed API**: Personalized item recommendations with filtering
- **Location-Based**: Distance-based filtering using Haversine formula
- **Soft Delete**: Items are archived rather than permanently deleted
- **Owner Verification**: Secure ownership checks for modifications
- **PostgreSQL Database**: Robust data persistence
- **Docker Support**: Easy deployment with Docker and Docker Compose

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/items` | Create a new item listing |
| `GET` | `/items/{item_id}` | Retrieve a single item by ID |
| `PUT` | `/items/{item_id}` | Update an existing item listing |
| `DELETE` | `/items/{item_id}` | Archive an item (soft delete) |
| `GET` | `/items/feed` | **[CORE MATCHING API]** Get items for swiping feed |
| `GET` | `/health` | Health check endpoint |

## Tech Stack

- **FastAPI**: Modern, fast web framework
- **Pydantic**: Data validation and serialization
- **SQLAlchemy**: SQL toolkit and ORM
- **PostgreSQL**: Relational database
- **Docker**: Containerization
- **Uvicorn**: ASGI server

## Quick Start

### Using Docker Compose (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Swappo-Catalog
   ```

2. **Start the services**
   ```bash
   docker-compose up -d
   ```

3. **Access the API**
   - API: http://localhost:8000
   - API Docs (Swagger): http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

4. **Optional: Start PgAdmin for database management**
   ```bash
   docker-compose --profile tools up -d
   ```
   - PgAdmin: http://localhost:5050 (admin@swappo.com / admin)

### Local Development

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start PostgreSQL** (if not using Docker)
   ```bash
   # Make sure PostgreSQL is running on localhost:5432
   ```

4. **Run the application**
   ```bash
   uvicorn main:app --reload
   ```

## API Usage Examples

### Create an Item
```bash
curl -X POST "http://localhost:8000/items" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Vintage Camera",
    "description": "Classic 35mm film camera in excellent condition",
    "category": "Electronics",
    "image_urls": ["https://example.com/image1.jpg"],
    "location_lat": 40.7128,
    "location_lon": -74.0060,
    "owner_id": "user123"
  }'
```

### Get Item Feed (Matching API)
```bash
curl -X GET "http://localhost:8000/items/feed?user_id=user456&limit=20&category=Electronics&distance=50&user_lat=40.7128&user_lon=-74.0060&exclude_item_ids=1,2,3"
```

### Update an Item
```bash
curl -X PUT "http://localhost:8000/items/1?owner_id=user123" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "swapped"
  }'
```

### Delete (Archive) an Item
```bash
curl -X DELETE "http://localhost:8000/items/1?owner_id=user123"
```

## Project Structure

```
Swappo-Catalog/
├── main.py              # FastAPI application and endpoints
├── models.py            # Pydantic and SQLAlchemy models
├── database.py          # Database configuration and session management
├── requirements.txt     # Python dependencies
├── Dockerfile          # Docker container configuration
├── docker-compose.yml  # Multi-container Docker setup
├── .env.example        # Environment variables template
├── .gitignore         # Git ignore rules
└── README.md          # This file
```

## Database Schema

### Items Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `name` | String(255) | Item name |
| `description` | Text | Item description |
| `category` | String(100) | Item category |
| `image_urls` | Array[String] | List of image URLs |
| `location_lat` | Float | Latitude coordinate |
| `location_lon` | Float | Longitude coordinate |
| `owner_id` | String(100) | Owner user ID |
| `status` | String(20) | active/archived/swapped |
| `created_at` | DateTime | Creation timestamp |
| `updated_at` | DateTime | Last update timestamp |

## Configuration

Environment variables can be set in a `.env` file:

```env
DATABASE_URL=postgresql://swappo_user:swappo_pass@localhost:5432/swappo_catalog
SQL_ECHO=false
```

## Development

### Running Tests
```bash
pytest
```

### Database Migrations
The application automatically creates tables on startup. For production, consider using Alembic for migrations.

### Code Style
- Follow PEP 8 guidelines
- Use type hints
- Add docstrings to functions and classes

## Deployment

### Production Considerations

1. **Security**
   - Change default passwords in `docker-compose.yml`
   - Use environment variables for sensitive data
   - Configure CORS appropriately
   - Implement authentication/authorization

2. **Performance**
   - Add database indexes
   - Implement caching (Redis)
   - Use connection pooling
   - Add rate limiting

3. **Monitoring**
   - Set up logging
   - Add application metrics
   - Configure health checks
   - Implement error tracking

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines Here]

## Support

For issues and questions, please open an issue on GitHub.
