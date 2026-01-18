import asyncio
import math
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from PIL import Image
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import and_, func
from sqlalchemy.orm import Session
from strawberry.fastapi import GraphQLRouter

# Import CQRS API
from cqrs_api import router as cqrs_router
from database import get_db, init_db

# Import gRPC server
from event_sourcing.command_handlers import CommandHandler
from event_sourcing.commands import (
    CreateItemCommand,
    DeleteItemCommand,
    UpdateItemCommand,
)
from gcs_storage import get_gcs_storage
from graphql_schema import get_context, schema
from grpc_server import serve_grpc
from metrics import (
    image_upload_size_bytes,
    image_uploads_total,
    items_created_total,
    record_http_request,
    update_item_metrics,
)
from models import (
    ErrorResponse,
    ItemCreate,
    ItemDB,
    ItemResponse,
    ItemStatus,
    ItemUpdate,
)

# Create uploads directory
UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup: Initialize database
    init_db()

    # Start gRPC server in background
    grpc_task = asyncio.create_task(serve_grpc())
    print("✅ gRPC server task created")

    yield

    # Shutdown: Cleanup
    grpc_task.cancel()
    try:
        await grpc_task
    except asyncio.CancelledError:
        print("✅ gRPC server stopped")
    pass


# Initialize FastAPI app
app = FastAPI(
    title="Swappo Catalog Service",
    description="""## Item Catalog & Management API

**Swappo Catalog Service** manages all item listings in the marketplace.

### Features
- Item CRUD operations (Create, Read, Update, Delete)
- Image upload and storage (GCS integration)
- Item search and filtering
- User item statistics
- GraphQL API for flexible queries
- gRPC service for inter-service communication
- Event Sourcing & CQRS pattern implementation

### Item Lifecycle
1. Upload item images at `/api/v1/items/upload`
2. Create item listing at `/api/v1/items`
3. Items appear in feed at `/api/v1/items/feed`
4. Update status (available/pending/swapped) via PATCH

### Storage
- Images stored in Google Cloud Storage bucket
- All item changes tracked in event store
- Support for event replay and audit trails
    """,
    version="1.0.0",
    contact={
        "name": "Swappo API Support",
        "url": "https://swappo.art",
        "email": "api@swappo.art",
    },
    license_info={
        "name": "MIT",
    },
    openapi_tags=[
        {"name": "Health", "description": "Service health and status endpoints"},
        {"name": "Items", "description": "Item listing CRUD operations"},
        {"name": "Images", "description": "Image upload and management"},
        {"name": "Feed", "description": "Discover items for swapping"},
        {"name": "Event Sourcing", "description": "CQRS and event store operations"},
        {"name": "GraphQL", "description": "GraphQL API for flexible queries"},
    ],
    root_path="/catalog",  # Fix for Kong reverse proxy - enables correct OpenAPI schema URLs
    lifespan=lifespan,
)

# Prometheus instrumentation
Instrumentator().instrument(app).expose(app, endpoint="/metrics")


# Middleware to track HTTP request metrics
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    # Skip metrics endpoint itself
    if request.url.path == "/metrics":
        return await call_next(request)

    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    record_http_request(
        method=request.method,
        endpoint=request.url.path,
        status_code=response.status_code,
        duration=duration,
    )

    return response


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for serving uploaded images
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Add GraphQL endpoint
graphql_app = GraphQLRouter(
    schema,
    context_getter=get_context,
)
app.include_router(graphql_app, prefix="/graphql", tags=["GraphQL"])

# Add CQRS/Event Sourcing endpoints
app.include_router(cqrs_router)


# Helper function to calculate distance between two coordinates (Haversine formula)
def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth (in kilometers).

    Args:
        lat1, lon1: Latitude and longitude of first point
        lat2, lon2: Latitude and longitude of second point

    Returns:
        Distance in kilometers
    """
    R = 6371  # Radius of Earth in kilometers

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {
        "service": "Swappo Catalog Service",
        "status": "running",
        "version": "1.0.0",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check endpoint"""
    return {"status": "healthy"}


@app.post(
    "/upload-image",
    tags=["Items"],
    summary="Upload an image for an item",
    responses={
        200: {"description": "Image uploaded successfully"},
        400: {"model": ErrorResponse, "description": "Invalid file"},
        413: {"model": ErrorResponse, "description": "File too large"},
    },
)
async def upload_image(file: UploadFile = File(...)):
    """
    Upload an image file and return the URL.

    Images are uploaded to Google Cloud Storage for production,
    or local filesystem for development.

    Args:
        file: Image file to upload

    Returns:
        dict with image_url

    Raises:
        HTTPException: If file is invalid or too large
    """
    import traceback
    from io import BytesIO

    try:
        print(f"Received file: {file.filename}, content_type: {file.content_type}")

        # Check file extension
        file_ext = Path(file.filename).suffix.lower()
        if not file_ext:
            file_ext = ".jpg"  # Default extension

        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}",
            )

        # Read file contents
        contents = await file.read()
        print(f"File size: {len(contents)} bytes")

        # Check file size
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE / (1024*1024)}MB",
            )

        # Verify it's a valid image using the contents
        try:
            img = Image.open(BytesIO(contents))
            img.verify()
            print(f"Image verified: {img.format}")
        except Exception as img_error:
            print(f"Image verification failed: {str(img_error)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid image file: {str(img_error)}",
            )

        # Upload to GCS if enabled, otherwise save locally
        use_gcs = os.getenv("USE_GCS", "true").lower() == "true"
        print(f"Using GCS: {use_gcs}")
        if use_gcs:
            try:
                # Upload to Google Cloud Storage
                gcs = get_gcs_storage()
                image_url = gcs.upload_image(
                    file_content=contents,
                    filename=file.filename,
                    content_type=file.content_type or "image/jpeg",
                )
                print(f"Image uploaded to GCS: {image_url}")
                # Record metrics
                image_uploads_total.labels(status="success").inc()
                image_upload_size_bytes.observe(len(contents))
                return {"image_url": image_url}
            except Exception as gcs_error:
                print(f"GCS upload failed, falling back to local: {gcs_error}")
                # Fall through to local storage

        # Local storage fallback (for development)
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = UPLOADS_DIR / unique_filename

        with open(file_path, "wb") as buffer:
            buffer.write(contents)

        print(f"File saved locally: {unique_filename}")
        # Record metrics
        image_uploads_total.labels(status="success").inc()
        image_upload_size_bytes.observe(len(contents))
        image_url = f"/catalog/uploads/{unique_filename}"
        return {"image_url": image_url}

    except HTTPException:
        image_uploads_total.labels(status="failed").inc()
        raise
    except Exception as e:
        image_uploads_total.labels(status="failed").inc()
        error_trace = traceback.format_exc()
        print(f"ERROR in upload_image: {str(e)}\n{error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}",
        )


@app.post(
    "/items",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Items"],
    summary="Create a new item listing",
    responses={
        201: {"description": "Item created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request data"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    """
    Create a new item listing.

    Uses Event Sourcing pattern:
    1. Validates request
    2. Creates CreateItemCommand
    3. Handles command (emits ItemCreatedEvent)
    4. Updates read model
    """
    try:
        # Use CQRS CommandHandler
        handler = CommandHandler(db)

        command = CreateItemCommand(
            user_id=item.owner_id,
            name=item.name,
            description=item.description,
            category=item.category,
            image_urls=item.image_urls,
            location_lat=item.location_lat,
            location_lon=item.location_lon,
            owner_id=item.owner_id,
        )

        item_id = handler.handle_create_item(command)

        # Record metrics
        items_created_total.inc()
        update_item_metrics(db)

        # Return the created item from the read model
        return db.query(ItemDB).filter(ItemDB.id == item_id).first()
    except Exception as e:
        print(f"Error creating item: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create item: {str(e)}",
        )


@app.get(
    "/items/my-items",
    response_model=List[ItemResponse],
    tags=["Items"],
    summary="Get all items owned by a specific user",
    responses={
        200: {"description": "User's items retrieved successfully"},
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
    },
)
async def get_my_items(
    owner_id: str = Query(..., description="User ID to fetch items for"),
    db: Session = Depends(get_db),
):
    """
    Retrieve all items owned by a specific user.

    Args:
        owner_id: User ID to fetch items for
        db: Database session

    Returns:
        List of items owned by the user
    """
    items = (
        db.query(ItemDB)
        .filter(
            and_(
                ItemDB.owner_id == owner_id, ItemDB.status != ItemStatus.archived.value
            )
        )
        .order_by(ItemDB.created_at.desc())
        .all()
    )

    return items


@app.get(
    "/items/feed",
    response_model=List[ItemResponse],
    tags=["Items", "Matching"],
    summary="[CORE MATCHING API] Retrieve items for swiping feed",
    responses={
        200: {"description": "Feed items retrieved successfully"},
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
    },
)
async def get_items_feed(
    limit: int = Query(20, ge=1, le=100, description="Number of items to retrieve"),
    user_id: str = Query(..., description="User ID requesting the feed"),
    exclude_item_ids: Optional[str] = Query(
        None, description="Comma-separated list of item IDs to exclude"
    ),
    category: Optional[str] = Query(None, description="Filter by category"),
    distance: Optional[float] = Query(
        None, ge=0, description="Maximum distance in kilometers"
    ),
    user_lat: Optional[float] = Query(
        None, ge=-90, le=90, description="User's latitude for distance filtering"
    ),
    user_lon: Optional[float] = Query(
        None, ge=-180, le=180, description="User's longitude for distance filtering"
    ),
    db: Session = Depends(get_db),
):
    """
    [CORE MATCHING API] Retrieves items suitable for swiping based on filters.

    This API is designed to be called by the MatchService to provide personalized
    item recommendations for users.

    Features:
    - Excludes user's own items
    - Excludes already swiped items
    - Filters by category (optional)
    - Filters by distance (optional, requires user location)
    - Returns only active items
    - Randomized order for discovery

    Args:
        limit: Number of items to return (1-100)
        user_id: User requesting the feed
        exclude_item_ids: Comma-separated IDs of items already swiped
        category: Filter by specific category
        distance: Maximum distance in km
        user_lat: User's latitude
        user_lon: User's longitude
        db: Database session

    Returns:
        List of items suitable for swiping
    """
    # Build base query - only active items, exclude user's own items
    query = db.query(ItemDB).filter(
        and_(ItemDB.status == ItemStatus.active.value, ItemDB.owner_id != user_id)
    )

    # Exclude already swiped items
    if exclude_item_ids:
        try:
            exclude_ids = [
                int(id.strip()) for id in exclude_item_ids.split(",") if id.strip()
            ]
            if exclude_ids:
                query = query.filter(ItemDB.id.notin_(exclude_ids))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid exclude_item_ids format. Must be comma-separated integers.",
            )

    # Filter by category
    if category:
        query = query.filter(ItemDB.category == category)

    # Fetch items
    items = query.order_by(func.random()).limit(limit).all()

    # Apply distance filtering if location is provided
    if distance is not None and user_lat is not None and user_lon is not None:
        filtered_items = []
        for item in items:
            item_distance = calculate_distance(
                user_lat, user_lon, item.location_lat, item.location_lon
            )
            if item_distance <= distance:
                filtered_items.append(item)
        items = filtered_items[:limit]
    elif (distance is not None) or (user_lat is not None) or (user_lon is not None):
        # If any distance-related param is provided, all must be provided
        if not all([distance is not None, user_lat is not None, user_lon is not None]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="For distance filtering, all of distance, user_lat, and user_lon must be provided",
            )

    return items


@app.get(
    "/items/{item_id}",
    response_model=ItemResponse,
    tags=["Items"],
    summary="Retrieve a single item by ID",
    responses={
        200: {"description": "Item found"},
        404: {"model": ErrorResponse, "description": "Item not found"},
    },
)
async def get_item(item_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a single item by ID.

    Args:
        item_id: Item ID
        db: Database session

    Returns:
        Item object

    Raises:
        HTTPException: If item not found
    """
    item = db.query(ItemDB).filter(ItemDB.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} not found",
        )
    return item


@app.put(
    "/items/{item_id}",
    response_model=ItemResponse,
    tags=["Items"],
    summary="Update an existing item listing",
    responses={
        200: {"description": "Item updated successfully"},
        403: {
            "model": ErrorResponse,
            "description": "Not authorized to update this item",
        },
        404: {"model": ErrorResponse, "description": "Item not found"},
    },
)
async def update_item(
    item_id: int,
    item_update: ItemUpdate,
    owner_id: str = Query(..., description="ID of the user making the request"),
    db: Session = Depends(get_db),
):
    """
    Update an existing item listing.

    Requires owner verification - only the owner can update their item.

    Args:
        item_id: Item ID
        item_update: Fields to update
        owner_id: Owner ID for verification
        db: Database session

    Returns:
        Updated item object

    Raises:
        HTTPException: If item not found or owner check fails
    """
    item = db.query(ItemDB).filter(ItemDB.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} not found",
        )

    # Owner check
    if item.owner_id != owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this item",
        )

    try:
        # Use CQRS CommandHandler
        handler = CommandHandler(db)

        # Prepare changes
        changes = item_update.model_dump(exclude_unset=True)
        # Convert status Enum to string value if present
        if "status" in changes and changes["status"]:
            changes["status"] = changes["status"].value

        command = UpdateItemCommand(user_id=owner_id, item_id=item_id, changes=changes)

        handler.handle_update_item(command)

        # Return updated item from read model
        db.refresh(item)
        return item

    except Exception as e:
        print(f"Error updating item: {e}")
        # Only rollback if we haven't committed in handler (handler usually commits)
        # But for safety in case handler failed before commit
        # db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update item: {str(e)}",
        )


@app.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Items"],
    summary="Remove an item listing (soft delete)",
    responses={
        204: {"description": "Item archived successfully"},
        403: {
            "model": ErrorResponse,
            "description": "Not authorized to delete this item",
        },
        404: {"model": ErrorResponse, "description": "Item not found"},
    },
)
async def delete_item(
    item_id: int,
    owner_id: str = Query(..., description="ID of the user making the request"),
    db: Session = Depends(get_db),
):
    """
    Remove an item listing by setting status to 'archived' (soft delete).

    Does not perform hard deletion - items are archived instead.

    Args:
        item_id: Item ID
        owner_id: Owner ID for verification
        db: Database session

    Raises:
        HTTPException: If item not found or owner check fails
    """
    item = db.query(ItemDB).filter(ItemDB.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} not found",
        )

    # Owner check
    if item.owner_id != owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this item",
        )

    # Soft delete - set status to archived
    # Used to use direct update, now uses Event Sourcing

    try:
        # Use CQRS CommandHandler
        handler = CommandHandler(db)

        command = DeleteItemCommand(
            user_id=owner_id, item_id=item_id, reason="User requested deletion"
        )

        handler.handle_delete_item(command)

    except Exception as e:
        print(f"Error deleting item: {e}")
        # db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to archive item: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
