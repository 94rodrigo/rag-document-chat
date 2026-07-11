#!/bin/bash
# Run from the backend/ directory
set -e
cd "$(dirname "$0")/.."

echo "Creating initial migration..."
alembic revision --autogenerate -m "initial_schema"
echo "Done. Review the generated file in migrations/versions/ before applying."
echo "Apply with: alembic upgrade head"
