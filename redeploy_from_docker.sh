#!/bin/bash

CONTAINER_NAME=mihais-ai-playground
IMAGE_NAME=cristianeduardmihai/mihais-ai-playground:latest

echo "Stopping and removing old container (if exists)..."
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true

echo "Removing old image (if exists)..."
docker rmi $IMAGE_NAME 2>/dev/null || true

echo "Pulling latest image..."
docker pull $IMAGE_NAME

echo "Starting new container..."
docker run -d --name $CONTAINER_NAME --restart unless-stopped -p 8084:8084 $IMAGE_NAME

echo "Done. App should be running on port 8084."