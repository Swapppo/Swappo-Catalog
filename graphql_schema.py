"""
GraphQL Schema for Catalog Service
Using Strawberry GraphQL with FastAPI integration
"""

import math
from enum import Enum
from typing import List, Optional

import strawberry
from sqlalchemy.orm import Session
from strawberry.types import Info

from database import get_db
from models import ItemDB, ItemStatus


# Helper function for distance calculation
def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points (Haversine formula)"""
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


# GraphQL Types
@strawberry.enum
class ItemStatusEnum(Enum):
    """Item status enum for GraphQL"""

    ACTIVE = "active"
    ARCHIVED = "archived"
    SWAPPED = "swapped"


@strawberry.type
class Item:
    """GraphQL type for Item"""

    id: int
    name: str
    description: str
    category: str
    image_urls: List[str]
    location_lat: float
    location_lon: float
    owner_id: str
    status: str
    created_at: str
    updated_at: str

    @strawberry.field
    def distance_from(self, lat: float, lon: float) -> float:
        """Calculate distance from a given location"""
        return calculate_distance(self.location_lat, self.location_lon, lat, lon)


@strawberry.type
class ItemConnection:
    """Paginated items response"""

    items: List[Item]
    total: int
    page: int
    page_size: int
    total_pages: int


@strawberry.input
class ItemFilterInput:
    """Filter options for querying items"""

    category: Optional[str] = None
    owner_id: Optional[str] = None
    status: Optional[str] = None
    search: Optional[str] = None


@strawberry.input
class LocationInput:
    """Location input for nearby search"""

    lat: float
    lon: float
    radius_km: Optional[float] = 10.0


@strawberry.input
class CreateItemInput:
    """Input for creating a new item"""

    name: str
    description: str
    category: str
    image_urls: List[str]
    location_lat: float
    location_lon: float
    owner_id: str


@strawberry.input
class UpdateItemInput:
    """Input for updating an item"""

    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    image_urls: Optional[List[str]] = None
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    status: Optional[str] = None


# Context for dependency injection
def get_context() -> dict:
    """Get context with database session"""
    db = next(get_db())
    return {"db": db}


# Query definitions
@strawberry.type
class Query:
    @strawberry.field
    def item(self, id: int, info: Info) -> Optional[Item]:
        """Get a single item by ID"""
        db: Session = info.context["db"]
        db_item = db.query(ItemDB).filter(ItemDB.id == id).first()

        if not db_item:
            return None

        return Item(
            id=db_item.id,
            name=db_item.name,
            description=db_item.description,
            category=db_item.category,
            image_urls=db_item.image_urls,
            location_lat=db_item.location_lat,
            location_lon=db_item.location_lon,
            owner_id=db_item.owner_id,
            status=db_item.status,
            created_at=db_item.created_at.isoformat(),
            updated_at=db_item.updated_at.isoformat(),
        )

    @strawberry.field
    def items(
        self,
        info: Info,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[ItemFilterInput] = None,
    ) -> ItemConnection:
        """Get paginated list of items with optional filters"""
        db: Session = info.context["db"]

        # Build query with filters
        query = db.query(ItemDB)

        if filters:
            if filters.category:
                query = query.filter(ItemDB.category == filters.category)
            if filters.owner_id:
                query = query.filter(ItemDB.owner_id == filters.owner_id)
            if filters.status:
                query = query.filter(ItemDB.status == filters.status)
            else:
                # Default: exclude archived items
                query = query.filter(ItemDB.status != ItemStatus.archived.value)

            if filters.search:
                search_term = f"%{filters.search}%"
                query = query.filter(
                    (ItemDB.name.ilike(search_term))
                    | (ItemDB.description.ilike(search_term))
                )
        else:
            # Default: exclude archived items
            query = query.filter(ItemDB.status != ItemStatus.archived.value)

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        db_items = (
            query.order_by(ItemDB.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        # Convert to GraphQL types
        items = [
            Item(
                id=item.id,
                name=item.name,
                description=item.description,
                category=item.category,
                image_urls=item.image_urls,
                location_lat=item.location_lat,
                location_lon=item.location_lon,
                owner_id=item.owner_id,
                status=item.status,
                created_at=item.created_at.isoformat(),
                updated_at=item.updated_at.isoformat(),
            )
            for item in db_items
        ]

        total_pages = math.ceil(total / page_size) if total > 0 else 0

        return ItemConnection(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @strawberry.field
    def items_nearby(
        self,
        info: Info,
        location: LocationInput,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[ItemFilterInput] = None,
    ) -> ItemConnection:
        """Get items near a specific location"""
        db: Session = info.context["db"]

        # Build base query with filters
        query = db.query(ItemDB)

        if filters:
            if filters.category:
                query = query.filter(ItemDB.category == filters.category)
            if filters.owner_id:
                query = query.filter(ItemDB.owner_id == filters.owner_id)
            if filters.status:
                query = query.filter(ItemDB.status == filters.status)
            else:
                query = query.filter(ItemDB.status != ItemStatus.archived.value)
        else:
            query = query.filter(ItemDB.status != ItemStatus.archived.value)

        # Get all items (we'll filter by distance in Python)
        all_items = query.all()

        # Filter by distance
        nearby_items = []
        for item in all_items:
            distance = calculate_distance(
                location.lat,
                location.lon,
                item.location_lat,
                item.location_lon,
            )
            if distance <= location.radius_km:
                nearby_items.append((item, distance))

        # Sort by distance
        nearby_items.sort(key=lambda x: x[1])

        # Apply pagination
        total = len(nearby_items)
        offset = (page - 1) * page_size
        paginated_items = nearby_items[offset : offset + page_size]

        # Convert to GraphQL types
        items = [
            Item(
                id=item.id,
                name=item.name,
                description=item.description,
                category=item.category,
                image_urls=item.image_urls,
                location_lat=item.location_lat,
                location_lon=item.location_lon,
                owner_id=item.owner_id,
                status=item.status,
                created_at=item.created_at.isoformat(),
                updated_at=item.updated_at.isoformat(),
            )
            for item, distance in paginated_items
        ]

        total_pages = math.ceil(total / page_size) if total > 0 else 0

        return ItemConnection(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @strawberry.field
    def categories(self, info: Info) -> List[str]:
        """Get list of all unique categories"""
        db: Session = info.context["db"]
        categories = db.query(ItemDB.category).distinct().all()
        return [cat[0] for cat in categories]


# Mutation definitions
@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_item(self, info: Info, input: CreateItemInput) -> Item:
        """Create a new item"""
        db: Session = info.context["db"]

        db_item = ItemDB(
            name=input.name,
            description=input.description,
            category=input.category,
            image_urls=input.image_urls,
            location_lat=input.location_lat,
            location_lon=input.location_lon,
            owner_id=input.owner_id,
            status=ItemStatus.active.value,
        )

        db.add(db_item)
        db.commit()
        db.refresh(db_item)

        return Item(
            id=db_item.id,
            name=db_item.name,
            description=db_item.description,
            category=db_item.category,
            image_urls=db_item.image_urls,
            location_lat=db_item.location_lat,
            location_lon=db_item.location_lon,
            owner_id=db_item.owner_id,
            status=db_item.status,
            created_at=db_item.created_at.isoformat(),
            updated_at=db_item.updated_at.isoformat(),
        )

    @strawberry.mutation
    def update_item(
        self, info: Info, id: int, input: UpdateItemInput
    ) -> Optional[Item]:
        """Update an existing item"""
        db: Session = info.context["db"]

        db_item = db.query(ItemDB).filter(ItemDB.id == id).first()
        if not db_item:
            return None

        # Update fields if provided
        if input.name is not None:
            db_item.name = input.name
        if input.description is not None:
            db_item.description = input.description
        if input.category is not None:
            db_item.category = input.category
        if input.image_urls is not None:
            db_item.image_urls = input.image_urls
        if input.location_lat is not None:
            db_item.location_lat = input.location_lat
        if input.location_lon is not None:
            db_item.location_lon = input.location_lon
        if input.status is not None:
            db_item.status = input.status

        db.commit()
        db.refresh(db_item)

        return Item(
            id=db_item.id,
            name=db_item.name,
            description=db_item.description,
            category=db_item.category,
            image_urls=db_item.image_urls,
            location_lat=db_item.location_lat,
            location_lon=db_item.location_lon,
            owner_id=db_item.owner_id,
            status=db_item.status,
            created_at=db_item.created_at.isoformat(),
            updated_at=db_item.updated_at.isoformat(),
        )

    @strawberry.mutation
    def delete_item(self, info: Info, id: int) -> bool:
        """Delete an item (soft delete by archiving)"""
        db: Session = info.context["db"]

        db_item = db.query(ItemDB).filter(ItemDB.id == id).first()
        if not db_item:
            return False

        db_item.status = ItemStatus.archived.value
        db.commit()

        return True


# Create the schema
schema = strawberry.Schema(query=Query, mutation=Mutation)
