#!/usr/bin/env bash
# Script to run all CI tasks
set -euo pipefail

# Define the directory containing the CI scripts
CI_DIR="tools/ci"

# Run each script in the CI directory
echo "Running all CI scripts..."
python "$CI_DIR/gen_er.py"
bash "$CI_DIR/gen_openapi.sh"  # This already includes npm run generate-types
python3 "$CI_DIR/gen_pipeline.py"
python3 "$CI_DIR/gen_schemas.py"

echo "All CI tasks completed successfully!"
