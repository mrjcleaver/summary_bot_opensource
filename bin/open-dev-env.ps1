$basePath = "$env:HOMEDRIVE$env:HOMEPATH\PycharmProjects\summary_bot_opensource"

function Start-NewWindow {
    param (
        [string]$Title,
        [string]$Command
    )

    $scriptBlock = @"
`$host.ui.RawUI.WindowTitle = '$Title'
Set-Location -Path '$basePath'
$Command
pause
"@

    Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", $scriptBlock
}

Start-NewWindow -Title "1. Fly Proxy" -Command "Write-Host fly proxy 5678:5678"
Start-NewWindow -Title "2. Fly Console" -Command "fly console; Set-Location diagnostics"
Start-NewWindow -Title "3. Fly Logs" -Command "fly logs"
Start-NewWindow -Title "4. Fly Deploy" -Command "Write-Host fly deploy --build-arg INSTALL_DEV=true"
Start-NewWindow -Title "5. Open Machines" -Command "Start-Process 'https://fly.io/apps/summary-bot-aparine/machines'"
Start-NewWindow -Title "Fly Local Shell" -Command "Write-Host 'Ready for commands...'"
