"""
gRPC Server Implementation for Catalog Service
Provides item information to other microservices
"""

import asyncio
from concurrent import futures

import grpc
from sqlalchemy.orm import Session

import catalog_pb2
import catalog_pb2_grpc
from database import get_db
from models import ItemDB


class CatalogServicer(catalog_pb2_grpc.CatalogServiceServicer):
    """Implementation of CatalogService gRPC server"""

    def GetItem(self, request, context):
        """Get a single item by ID"""
        db: Session = next(get_db())

        try:
            item = db.query(ItemDB).filter(ItemDB.id == request.item_id).first()

            if not item:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Item with ID {request.item_id} not found")
                return catalog_pb2.ItemResponse()

            return catalog_pb2.ItemResponse(
                id=item.id,
                name=item.name,
                description=item.description or "",
                category=item.category,
                image_urls=item.image_urls or [],
                location_lat=item.location_lat,
                location_lon=item.location_lon,
                owner_id=item.owner_id,
                status=item.status,
                created_at=item.created_at.isoformat() if item.created_at else "",
                updated_at=item.updated_at.isoformat() if item.updated_at else "",
            )
        finally:
            db.close()

    def GetItems(self, request, context):
        """Get multiple items by IDs (batch request)"""
        db: Session = next(get_db())

        try:
            items = db.query(ItemDB).filter(ItemDB.id.in_(request.item_ids)).all()

            found_ids = {item.id for item in items}
            not_found_ids = [
                item_id for item_id in request.item_ids if item_id not in found_ids
            ]

            item_responses = [
                catalog_pb2.ItemResponse(
                    id=item.id,
                    name=item.name,
                    description=item.description or "",
                    category=item.category,
                    image_urls=item.image_urls or [],
                    location_lat=item.location_lat,
                    location_lon=item.location_lon,
                    owner_id=item.owner_id,
                    status=item.status,
                    created_at=item.created_at.isoformat() if item.created_at else "",
                    updated_at=item.updated_at.isoformat() if item.updated_at else "",
                )
                for item in items
            ]

            return catalog_pb2.GetItemsResponse(
                items=item_responses, not_found_ids=not_found_ids
            )
        finally:
            db.close()

    def ValidateItems(self, request, context):
        """Check if items exist and are active"""
        db: Session = next(get_db())

        try:
            items = db.query(ItemDB).filter(ItemDB.id.in_(request.item_ids)).all()

            # Create a dict for quick lookup
            items_dict = {item.id: item for item in items}

            validations = []
            for item_id in request.item_ids:
                if item_id in items_dict:
                    item = items_dict[item_id]
                    validations.append(
                        catalog_pb2.ItemValidation(
                            item_id=item_id,
                            exists=True,
                            is_active=(item.status == "active"),
                            owner_id=item.owner_id,
                        )
                    )
                else:
                    validations.append(
                        catalog_pb2.ItemValidation(
                            item_id=item_id, exists=False, is_active=False, owner_id=""
                        )
                    )

            return catalog_pb2.ValidateItemsResponse(validations=validations)
        finally:
            db.close()


async def serve_grpc():
    """Start the gRPC server"""
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    catalog_pb2_grpc.add_CatalogServiceServicer_to_server(CatalogServicer(), server)

    listen_addr = "[::]:50051"
    server.add_insecure_port(listen_addr)

    print(f"🚀 gRPC Server starting on {listen_addr}")
    await server.start()

    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        print("⏹️ Shutting down gRPC server")
        await server.stop(grace=5)


if __name__ == "__main__":
    asyncio.run(serve_grpc())
