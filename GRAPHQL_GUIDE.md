# GraphQL Implementation for Swappo Catalog Service

## Overview

The Catalog service now supports **both REST and GraphQL APIs** running side-by-side:
- **REST API**: Traditional endpoints at `/items`, `/upload-image`, etc.
- **GraphQL API**: Single endpoint at `/graphql` with queries and mutations

## Why GraphQL?

GraphQL offers several advantages over REST:
- **Flexible Queries**: Clients request exactly what they need
- **Single Request**: Get related data in one query instead of multiple REST calls
- **Strongly Typed**: Built-in schema validation and autocomplete
- **Real-time**: Easy to add subscriptions later
- **Better Performance**: Reduces over-fetching and under-fetching


- **GKE/Kong**: http://34.40.17.122.nip.io/catalog/graphql

The playground provides:
- ✅ Auto-completion
- ✅ Schema documentation
- ✅ Query builder
- ✅ Real-time query execution

## GraphQL Schema

### Types

```graphql
type Item {
  id: Int!
  name: String!
  description: String!
  category: String!
  imageUrls: [String!]!
  locationLat: Float!
  locationLon: Float!
  ownerId: String!
  status: String!
  createdAt: String!
  updatedAt: String!

  # Computed field: calculate distance from a location
  distanceFrom(lat: Float!, lon: Float!): Float!
}

type ItemConnection {
  items: [Item!]!
  total: Int!
  page: Int!
  pageSize: Int!
  totalPages: Int!
}
```

### Queries

```graphql
type Query {
  # Get single item by ID
  item(id: Int!): Item

  # Get paginated items with filters
  items(
    page: Int = 1
    pageSize: Int = 20
    filters: ItemFilterInput
  ): ItemConnection!

  # Get items near a location
  itemsNearby(
    location: LocationInput!
    page: Int = 1
    pageSize: Int = 20
    filters: ItemFilterInput
  ): ItemConnection!

  # Get all unique categories
  categories: [String!]!
}
```

### Mutations

```graphql
type Mutation {
  # Create a new item
  createItem(input: CreateItemInput!): Item!

  # Update an existing item
  updateItem(id: Int!, input: UpdateItemInput!): Item

  # Delete (archive) an item
  deleteItem(id: Int!): Boolean!
}
```

## Example Queries

### 1. Get Single Item

```graphql
query GetItem {
  item(id: 1) {
    id
    name
    description
    category
    imageUrls
    ownerId
    status
  }
}
```

### 2. Get Items with Pagination

```graphql
query GetItems {
  items(page: 1, pageSize: 10) {
    items {
      id
      name
      category
      imageUrls
      ownerId
    }
    total
    totalPages
  }
}
```

### 3. Filter Items by Category

```graphql
query GetToolsCategory {
  items(
    page: 1
    pageSize: 20
    filters: { category: "Tools" }
  ) {
    items {
      id
      name
      description
      imageUrls
    }
    total
  }
}
```

### 4. Search Items

```graphql
query SearchItems {
  items(
    filters: { search: "shovel" }
  ) {
    items {
      id
      name
      description
      category
    }
    total
  }
}
```

### 5. Get Items by Owner

```graphql
query GetMyItems {
  items(
    filters: { ownerId: "user123" }
  ) {
    items {
      id
      name
      status
      createdAt
    }
    total
  }
}
```

### 6. Get Nearby Items (Location-based)

```graphql
query GetNearbyItems {
  itemsNearby(
    location: { lat: 46.0569, lon: 14.5058, radiusKm: 10 }
    page: 1
    pageSize: 20
  ) {
    items {
      id
      name
      category
      distanceFrom(lat: 46.0569, lon: 14.5058)
    }
    total
  }
}
```

### 7. Get Nearby Items with Category Filter

```graphql
query GetNearbyTools {
  itemsNearby(
    location: { lat: 46.0569, lon: 14.5058, radiusKm: 5 }
    filters: { category: "Tools" }
  ) {
    items {
      id
      name
      description
      distanceFrom(lat: 46.0569, lon: 14.5058)
    }
    total
  }
}
```

### 8. Get All Categories

```graphql
query GetCategories {
  categories
}
```

## Example Mutations

### 1. Create Item

```graphql
mutation CreateItem {
  createItem(
    input: {
      name: "Garden Shovel"
      description: "Heavy-duty steel shovel, perfect for gardening"
      category: "Tools"
      imageUrls: ["/uploads/shovel.jpg"]
      locationLat: 46.0569
      locationLon: 14.5058
      ownerId: "user123"
    }
  ) {
    id
    name
    status
    createdAt
  }
}
```

### 2. Update Item

```graphql
mutation UpdateItem {
  updateItem(
    id: 1
    input: {
      name: "Updated Item Name"
      description: "Updated description"
      status: "active"
    }
  ) {
    id
    name
    description
    status
    updatedAt
  }
}
```

### 3. Delete (Archive) Item

```graphql
mutation DeleteItem {
  deleteItem(id: 1)
}
```

## Complex Queries

### Get Multiple Related Data in One Request

Instead of 3 REST calls, do one GraphQL query:

```graphql
query ComplexQuery {
  # Get all categories
  categories

  # Get my items
  myItems: items(filters: { ownerId: "user123" }) {
    items {
      id
      name
      imageUrls
      status
    }
    total
  }

  # Get nearby items (excluding mine)
  nearbyItems: itemsNearby(
    location: { lat: 46.0569, lon: 14.5058, radiusKm: 10 }
  ) {
    items {
      id
      name
      category
      distanceFrom(lat: 46.0569, lon: 14.5058)
    }
    total
  }

  # Get a specific item
  specificItem: item(id: 5) {
    id
    name
    description
    imageUrls
    ownerId
  }
}
```

## Using GraphQL with Your Frontend

### React/React Native Example

```typescript
import { gql } from '@apollo/client';

// Query
const GET_ITEMS = gql`
  query GetItems($page: Int!, $category: String) {
    items(page: $page, filters: { category: $category }) {
      items {
        id
        name
        description
        imageUrls
        category
      }
      total
      totalPages
    }
  }
`;

// Usage
const { data, loading, error } = useQuery(GET_ITEMS, {
  variables: { page: 1, category: "Tools" }
});
```

### Fetch API Example

```javascript
const query = `
  query GetNearbyItems($lat: Float!, $lon: Float!) {
    itemsNearby(location: { lat: $lat, lon: $lon, radiusKm: 10 }) {
      items {
        id
        name
        imageUrls
      }
      total
    }
  }
`;

const response = await fetch('http://34.40.17.122.nip.io/catalog/graphql', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    query,
    variables: { lat: 46.0569, lon: 14.5058 }
  })
});

const { data } = await response.json();
```

## Integration with Kong

Kong works perfectly with GraphQL! Your endpoint will be:

```
http://34.40.17.122.nip.io/catalog/graphql
```

All Kong features work with GraphQL:
- ✅ Rate limiting
- ✅ CORS
- ✅ Authentication (add JWT plugin if needed)
- ✅ Caching
- ✅ Logging

### Kong Rate Limiting with GraphQL

GraphQL queries count as single requests, so rate limiting works normally. Complex queries still count as 1 request!

## Testing

### Using curl

```powershell
# Simple query
curl -X POST http://localhost:8002/graphql `
  -H "Content-Type: application/json" `
  -d '{\"query\":\"{ categories }\"}'

# Query with variables
curl -X POST http://localhost:8002/graphql `
  -H "Content-Type: application/json" `
  -d '{\"query\":\"query($id: Int!) { item(id: $id) { name } }\",\"variables\":{\"id\":1}}'
```

### Using GraphQL Playground

1. Navigate to: http://localhost:8002/graphql
2. Paste query on the left
3. Click "Play" button
4. See results on the right

## Performance Advantages

### Before (REST):
```
GET /items?owner_id=user123          → 100ms
GET /items?category=Tools&limit=10   → 120ms
GET /items/nearby?lat=46&lon=14      → 150ms
-----------------
Total: 3 requests, 370ms
```

### After (GraphQL):
```graphql
query {
  myItems: items(filters: { ownerId: "user123" }) { ... }
  tools: items(filters: { category: "Tools" }) { ... }
  nearby: itemsNearby(location: { lat: 46, lon: 14 }) { ... }
}
```
```
Total: 1 request, ~150ms
```

## REST vs GraphQL Comparison

| Feature | REST | GraphQL |
|---------|------|---------|
| **Endpoints** | Multiple (`/items`, `/items/:id`, etc.) | Single (`/graphql`) |
| **Data Fetching** | Fixed response structure | Client specifies fields |
| **Multiple Resources** | Multiple requests | Single request |
| **Over-fetching** | Common (gets all fields) | Never (request only needed fields) |
| **Under-fetching** | Common (need more requests) | Never (get all related data) |
| **Versioning** | URL versioning (`/v1/items`) | Schema evolution (no versioning) |
| **Documentation** | Manual (OpenAPI) | Auto-generated (introspection) |
| **Type Safety** | Depends on implementation | Built-in |

## Best Practices

1. **Use GraphQL for complex queries** - When you need related data from multiple sources
2. **Use REST for simple operations** - Image uploads, health checks, etc.
3. **Request only needed fields** - Don't request everything in GraphQL
4. **Use pagination** - Always paginate large result sets
5. **Add authentication** - Validate `owner_id` matches logged-in user (add later)

## Next Steps

### Add Authentication
```python
# In graphql_schema.py
@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_item(self, info: Info, input: CreateItemInput) -> Item:
        # Verify user from JWT token
        user_id = info.context.get("user_id")
        if not user_id:
            raise Exception("Unauthorized")

        # Ensure owner_id matches authenticated user
        if input.owner_id != user_id:
            raise Exception("Cannot create item for another user")

        # ... rest of mutation
```

### Add Subscriptions (Real-time)
```python
@strawberry.type
class Subscription:
    @strawberry.subscription
    async def item_created(self) -> AsyncGenerator[Item, None]:
        # Notify when new items are created
        pass
```

### Add DataLoaders (Prevent N+1)
```python
# Optimize queries when fetching related data
from strawberry.dataloader import DataLoader
```

## Troubleshooting

### GraphQL endpoint returns 404
- Make sure you rebuilt the container: `docker-compose build catalog-service`
- Check if strawberry is installed: `pip list | grep strawberry`

### "No module named 'graphql_schema'"
- Restart the service after adding the file
- Check file is in the same directory as main.py

### Queries are slow
- Check database indices on filtered columns
- Use pagination (don't request all items at once)
- Consider adding DataLoader for N+1 query problems

## Resources

- [Strawberry GraphQL Docs](https://strawberry.rocks/)
- [GraphQL Official Docs](https://graphql.org/)
- [GraphQL Best Practices](https://graphql.org/learn/best-practices/)
