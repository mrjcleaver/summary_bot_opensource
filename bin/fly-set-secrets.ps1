# This powershell script sets Fly.io secrets using environment variables set up in the Linux formatted .env file.
# Dependencies: setenv.ps1 - Script to set required environment variables

$envFilePath = "../.env"

# Check if the .env file exists
if (!(Test-Path -Path $envFilePath)) {
  Write-Error "Required .env file not found at $envFilePath. Please create this file with your environment variables."
  exit 1
}

# Read and parse the .env file
Get-Content -Path $envFilePath | ForEach-Object {
  # Ignore empty lines and comments
  if ($_ -match "^\s*#|^\s*$") { return }

  # Parse key-value pairs
  if ($_ -match "^\s*([^=]+)\s*=\s*(.+)\s*$") {
      $key = $matches[1].Trim()
      $value = $matches[2].Trim()

      # Remove quotes if present
      $value = $value -replace '^"|"$', ''

      # Set the environment variable
      [System.Environment]::SetEnvironmentVariable($key, $value, [System.EnvironmentVariableTarget]::Process)
  }
}

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

  if ($LASTEXITCODE -ne 0) {
       Write-Error "Failed to set Fly.io secrets. Make sure you're logged in to Fly.io."
       exit 1
  }


fly secrets list
  if ($LASTEXITCODE -ne 0) {
     Write-Error "Failed to list Fly.io secrets. Make sure you're logged in to Fly.io."
     exit 1
  }
  