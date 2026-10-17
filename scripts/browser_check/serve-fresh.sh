#!/bin/sh
# Start the app on port 8765 with a throwaway database, for run.mjs. Stops any previous one.
cd "$(dirname "$0")/../.." || exit 1
pkill -f "frontdesk-check-server" 2>/dev/null
sleep 0.5
rm -f var/check.db
.venv/bin/python -c "import uvicorn; from pathlib import Path; from app.main import create_app; uvicorn.run(create_app(db_path=Path('var/check.db')), port=8765, log_level='warning')  # frontdesk-check-server" > var/check-server.log 2>&1 &
for i in $(seq 1 40); do curl -s localhost:8765/api/health >/dev/null && exit 0; sleep 0.25; done
echo "server did not start; see var/check-server.log" >&2
exit 1
