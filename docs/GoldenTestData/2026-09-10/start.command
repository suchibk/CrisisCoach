#!/bin/bash
# Crisis Coach prototype — double-click this file on a Mac.
# It serves this folder on port 8000 and opens the prototype in your browser.
cd "$(dirname "$0")" || exit 1
PORT=8000
while lsof -ti :$PORT >/dev/null 2>&1; do
  echo "Port $PORT is busy, trying $((PORT+1))…"
  PORT=$((PORT+1))
done
echo "Crisis Coach is running at  http://localhost:$PORT/crisis-coach-prototype.html"
echo "Leave this window open. Press Ctrl-C to stop."
( sleep 1; open "http://localhost:$PORT/crisis-coach-prototype.html" ) &
python3 -m http.server $PORT
