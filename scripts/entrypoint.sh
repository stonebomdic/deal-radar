#!/usr/bin/env bash
set -euo pipefail

echo "=== Credit Card Crawler - Starting Up ==="

DB_PATH="/app/data/credit_cards.db"

# Step 1: Initialize database if it does not exist
if [ ! -f "$DB_PATH" ]; then
    echo ">>> Database not found. Initializing..."
    python -m src.cli init
    echo ">>> Database initialized."
else
    echo ">>> Database already exists. Skipping init."
fi

# Step 2: Seed bank data if the database is empty (file size < 20KB means no real data)
DB_SIZE=$(stat -c%s "$DB_PATH" 2>/dev/null || stat -f%z "$DB_PATH" 2>/dev/null || echo "0")
if [ "$DB_SIZE" -lt 20480 ]; then
    echo ">>> Database appears empty. Running seed..."
    python -m src.cli seed
    echo ">>> Seed complete."
else
    echo ">>> Database has data. Skipping seed."
fi

# Step 3: Start the server (or run whatever command was passed as arguments)
if [ $# -gt 0 ]; then
    echo ">>> Executing custom command: $*"
    exec "$@"
else
    echo ">>> Starting API server..."
    exec python -m src.cli serve
fi
