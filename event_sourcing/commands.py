"""
Commands for CQRS - Write side.
Commands express intent to change state.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class Command(BaseModel):
    """Base class for all commands"""

    user_id: str  # Who is executing the command


class CreateItemCommand(Command):
    """Command to create a new item"""

    name: str
    description: str
    category: str
    image_urls: List[str]
    location_lat: float
    location_lon: float
    owner_id: str


class UpdateItemCommand(Command):
    """Command to update an item"""

    item_id: int
    changes: Dict[str, Any]  # Fields to update


class ChangeItemStatusCommand(Command):
    """Command to change item status"""

    item_id: int
    new_status: str
    reason: Optional[str] = None


class DeleteItemCommand(Command):
    """Command to delete an item"""

    item_id: int
    reason: Optional[str] = None
