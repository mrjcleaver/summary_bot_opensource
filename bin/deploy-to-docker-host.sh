#!/bin/bash

if [ -f ".env" ]; then
    echo "Loading environment variables from .env file"
else
    echo ".env file not found, error."
    exit 1
fi
. .env

if [ -n "$DOCKER_HOST" ]; then
    echo "DOCKER_HOST is set to $DOCKER_HOST"
else
    echo "DOCKER_HOST is not set, error."
    exit 1
fi

# SSH into the remote server and load the image
docker compose -f docker-compose.yaml --env-file .env up -d --build 
docker compose logs -f