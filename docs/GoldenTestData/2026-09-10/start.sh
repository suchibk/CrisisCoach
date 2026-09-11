#!/bin/bash
# Linux / WSL. On Windows use:  python -m http.server 8000
cd "$(dirname "$0")" || exit 1
echo "http://localhost:8000/crisis-coach-prototype.html"
python3 -m http.server 8000
