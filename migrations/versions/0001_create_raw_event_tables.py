from __future__ import annotations

from alembic import op

revision = "0001_create_raw_event_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    op.execute(
        """
        CREATE TABLE raw_events (
            event_time TIMESTAMPTZ NOT NULL,
            ingested_at TIMESTAMPTZ NOT NULL,
            source TEXT NOT NULL,
            symbol TEXT NOT NULL,
            event_type TEXT NOT NULL,
            trade_id BIGINT NULL,
            update_id BIGINT NULL,
            raw_payload_hash TEXT NOT NULL,
            payload JSONB NOT NULL,
            PRIMARY KEY (source, symbol, event_type, event_time, raw_payload_hash)
        );
        """
    )
    op.execute(
        """
        SELECT create_hypertable(
            'raw_events',
            'event_time',
            if_not_exists => TRUE
        );
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX raw_events_trade_identity_idx ON raw_events
        (source, symbol, event_type, event_time, trade_id, raw_payload_hash)
        WHERE event_type = 'trade' AND trade_id IS NOT NULL;
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX raw_events_book_ticker_identity_idx ON raw_events
        (source, symbol, event_type, event_time, update_id, raw_payload_hash)
        WHERE event_type = 'book_ticker' AND update_id IS NOT NULL;
        """
    )
    op.execute(
        """
        CREATE INDEX raw_events_symbol_replay_idx
        ON raw_events (
            source,
            symbol,
            event_time,
            ingested_at,
            event_type,
            trade_id,
            update_id,
            raw_payload_hash
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE raw_events")
