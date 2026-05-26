#!/bin/bash
# MSCM Daily Job Search Pipeline
# Usage: ./run.sh [full|scrape|score|report]

set -e
cd "$(dirname "$0")"

# Check AWS credentials before scoring
if [ "$1" != "scrape" ]; then
    if ! aws sts get-caller-identity &>/dev/null; then
        echo "AWS credentials expired. Run: aws sso login"
        echo "(Scraping still works without credentials — only scoring needs AWS)"
        if [ "$1" = "score" ]; then
            exit 1
        fi
    fi
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
