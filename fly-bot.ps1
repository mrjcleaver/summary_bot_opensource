. .\setenv.ps1

if (-not $env:DISCORD_TOKEN) {
    throw "Environment variable DISCORD_TOKEN is not set. Aborting script."
}

if (-not $env:OPENAI_API_KEY) {
    throw "Environment variable OPENAI_API_KEY is not set. Aborting script."
}

fly secrets set `
  FLASK_APP="src/main.py" `
  DISCORD_TOKEN="$env:DISCORD_TOKEN" `
  OPENAI_API_KEY="$env:OPENAI_API_KEY"

fly secrets list
