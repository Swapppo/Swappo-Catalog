from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

Base = declarative_base()


class ItemStatus(str, Enum):
    """Item status enum"""
    active = "active"
    archived = "archived"
    swapped = "swapped"


# SQLAlchemy Models (Database)
class ItemDB(Base):
    """SQLAlchemy model for items table"""
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False, index=True)
    image_urls = Column(ARRAY(String), nullable=False)
    location_lat = Column(Float, nullable=False)
    location_lon = Column(Float, nullable=False)
    owner_id = Column(String(100), nullable=False, index=True)
    status = Column(String(20), nullable=False, default=ItemStatus.active.value, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


# Pydantic Models (Request/Response)
class ItemBase(BaseModel):
    """Base item schema"""
    name: str = Field(..., min_length=1, max_length=255, description="Item name")
    description: str = Field(..., min_length=1, description="Item description")
    category: str = Field(..., min_length=1, max_length=100, description="Item category")
    image_urls: List[str] = Field(..., min_items=1, description="List of image URLs")
    location_lat: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    location_lon: float = Field(..., ge=-180, le=180, description="Longitude coordinate")
    owner_id: str = Field(..., min_length=1, max_length=100, description="Owner user ID")


class ItemCreate(ItemBase):
    """Schema for creating an item"""
    pass


class ItemUpdate(BaseModel):
    """Schema for updating an item"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    image_urls: Optional[List[str]] = Field(None, min_items=1)
    location_lat: Optional[float] = Field(None, ge=-90, le=90)
    location_lon: Optional[float] = Field(None, ge=-180, le=180)
    status: Optional[ItemStatus] = None


class ItemResponse(ItemBase):
    """Schema for item response"""
    id: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ItemFeedParams(BaseModel):
    """Schema for feed query parameters"""
    limit: int = Field(default=20, ge=1, le=100, description="Number of items to retrieve")
    user_id: str = Field(..., min_length=1, description="User ID requesting the feed")
    exclude_item_ids: Optional[List[int]] = Field(default=None, description="List of item IDs to exclude")
    category: Optional[str] = Field(default=None, description="Filter by category")
    distance: Optional[float] = Field(default=None, ge=0, description="Maximum distance in kilometers")
    user_lat: Optional[float] = Field(default=None, ge=-90, le=90, description="User's latitude")
    user_lon: Optional[float] = Field(default=None, ge=-180, le=180, description="User's longitude")


class ErrorResponse(BaseModel):
    """Standard error response"""
    detail: str
