"""
Queries for CQRS - Read side.
Queries read from optimized read models, never from event store directly.
"""

from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import ItemDB, ItemStatus


class QueryHandler:
    """
    Handles queries against read models.
    This is the READ side of CQRS.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_item_by_id(self, item_id: int) -> Optional[ItemDB]:
        """Get single item by ID"""
        return self.db.query(ItemDB).filter(ItemDB.id == item_id).first()

    def get_items_by_owner(
        self, owner_id: str, status: Optional[ItemStatus] = None
    ) -> List[ItemDB]:
        """Get all items for an owner"""
        query = self.db.query(ItemDB).filter(ItemDB.owner_id == owner_id)

        if status:
            query = query.filter(ItemDB.status == status.value)

        return query.all()

    def get_items_by_category(
        self, category: str, status: ItemStatus = ItemStatus.active
    ) -> List[ItemDB]:
        """Get items by category"""
        return (
            self.db.query(ItemDB)
            .filter(ItemDB.category == category, ItemDB.status == status.value)
            .all()
        )

    def search_items(
        self,
        search_term: Optional[str] = None,
        category: Optional[str] = None,
        status: ItemStatus = ItemStatus.active,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ItemDB]:
        """
        Search items with various filters.
        This demonstrates how read models can be optimized for queries.
        """
        query = self.db.query(ItemDB).filter(ItemDB.status == status.value)

        if search_term:
            search_filter = f"%{search_term}%"
            query = query.filter(
                ItemDB.name.ilike(search_filter)
                | ItemDB.description.ilike(search_filter)
            )

        if category:
            query = query.filter(ItemDB.category == category)

        return query.limit(limit).offset(offset).all()

    def get_item_statistics(self) -> dict:
        """
        Get statistics about items.
        Example of a complex read model query.
        """
        total_items = self.db.query(func.count(ItemDB.id)).scalar()

        active_items = (
            self.db.query(func.count(ItemDB.id))
            .filter(ItemDB.status == ItemStatus.active.value)
            .scalar()
        )

        swapped_items = (
            self.db.query(func.count(ItemDB.id))
            .filter(ItemDB.status == ItemStatus.swapped.value)
            .scalar()
        )

        items_by_category = (
            self.db.query(ItemDB.category, func.count(ItemDB.id))
            .group_by(ItemDB.category)
            .all()
        )

        return {
            "total_items": total_items,
            "active_items": active_items,
            "swapped_items": swapped_items,
            "by_category": {cat: count for cat, count in items_by_category},
        }
