#!/bin/bash
# MSCM Daily Job Search Pipeline
# Usage: ./run.sh [full|scrape|score|report]

set -e
cd "$(dirname "$0")"

# Load .env if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

MODE=${1:-full}

case $MODE in
    full)
        python -m src.pipeline
        ;;
    scrape)
        python -m src.pipeline scrape
        ;;
    score)
        python -m src.pipeline score
        ;;
    report)
        python -m src.pipeline report
        ;;
    *)
        echo "Usage: ./run.sh [full|scrape|score|report]"
        exit 1
        ;;
esac
