"""
Database migration script to create event_store table.

Run this after deploying to create the event_store table.
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://swappo_user:swappo_pass@localhost:5432/swappo_catalog"
)

# SQL to create event_store table
CREATE_EVENT_STORE_SQL = """
CREATE TABLE IF NOT EXISTS event_store (
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

CREATE INDEX IF NOT EXISTS idx_event_id ON event_store(event_id);
CREATE INDEX IF NOT EXISTS idx_aggregate ON event_store(aggregate_id, aggregate_type);
CREATE INDEX IF NOT EXISTS idx_event_type_timestamp ON event_store(event_type, timestamp);
CREATE INDEX IF NOT EXISTS idx_timestamp ON event_store(timestamp);
"""


def migrate():
    """Run the migration"""
    print("🔄 Creating event_store table...")
    print(f"   Database: {DATABASE_URL.split('@')[1]}")  # Hide password

    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Execute migration
        conn.execute(text(CREATE_EVENT_STORE_SQL))
        conn.commit()

        # Verify table exists
        result = conn.execute(
            text(
                """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name = 'event_store'
        """
            )
        )

        count = result.scalar()

        if count > 0:
            print("✅ event_store table created successfully!")

            # Show table structure
            result = conn.execute(
                text(
                    """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'event_store'
                ORDER BY ordinal_position
            """
                )
            )

            print("\n   Table structure:")
            for row in result:
                print(f"      - {row[0]}: {row[1]}")

            # Show indexes
            result = conn.execute(
                text(
                    """
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'event_store'
            """
                )
            )

            print("\n   Indexes:")
            for row in result:
                print(f"      - {row[0]}")
        else:
            print("❌ Failed to create event_store table")

    print("\n✅ Migration complete!")


if __name__ == "__main__":
    migrate()
