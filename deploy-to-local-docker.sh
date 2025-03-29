#!/bin/bash

REMOTE_HOST="mrjc@docker-host.33.cleaver.org"

# SSH into the remote server and load the image
export DOCKER_HOST=ssh://mrjc@docker-host.33.cleaver.org
docker compose --env-file .env up -d --build 
docker compose logs -f