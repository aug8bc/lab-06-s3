#!/bin/bash
set -euo pipefail

if [ "$#" -ne 3 ]; then
	echo "Usage: $0 BOOK_URL BUCKET EXPIRES_SECONDS" >&2
	exit 1
fi

URL="$1"
BUCKET="$2"
EXPIRATION="$3"

FILENAME="$(basename "$URL")"
LOCAL_PATH="books/$FILENAME"

mkdir -p books
curl -fsSL "$URL" -o "$LOCAL_PATH"

if aws s3 ls "s3://$BUCKET" > /dev/null 2>&1; then
	echo "Bucket $BUCKET already exists"
else
	aws s3 mb "s3://$BUCKET" --region us-east-1
fi

aws s3 cp "$LOCAL_PATH" "s3://$BUCKET/$FILENAME" \
	--content-type "text/plain; charset=utf-8"

echo "URL (expires in $EXPIRATION seconds):"
aws s3 presign "s3://$BUCKET/$FILENAME" --expires-in "$EXPIRATION"
