#!/usr/bin/env bash
# run_demo.sh — regenerates all pipeline data (optional) and starts the
# dashboard's local server in one step.
#
# Usage:
#   ./run_demo.sh            # just start the dashboard using existing data
#   ./run_demo.sh --rebuild  # regenerate data through the full pipeline first

set -e
cd "$(dirname "$0")"

if [ "$1" == "--rebuild" ]; then
  echo ">> Rebuilding data through the full pipeline..."
  cd data_pipeline
  python3 01_generate_data.py
  python3 02_fuse_and_train.py
  python3 03_inundation_mapping.py
  python3 04_export_demo_bundle.py
  cd ..
fi

echo ">> Starting dashboard server at http://localhost:8000 ..."
cd frontend
python3 -m http.server 8000
