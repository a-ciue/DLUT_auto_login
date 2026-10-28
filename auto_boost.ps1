# Run with PowerShell 7 (pwsh).
$ErrorActionPreference = "Stop"
$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$LoginScript = Join-Path $PSScriptRoot "dlut_autologin.py"
$ConfigFile = Join-Path $PSScriptRoot "config.local.json"

foreach ($RequiredFile in @($Python, $LoginScript, $ConfigFile)) {
    if (-not (Test-Path -LiteralPath $RequiredFile -PathType Leaf)) {
        throw "Missing required file: $RequiredFile. See README.md for setup."
    }
}

while ($true) {
    while ($true) {
        Write-Host "正在刷新适配器..."
        ipconfig.exe /release
        ipconfig.exe /renew
        Start-Sleep -Seconds 3

        & $Python $LoginScript --config $ConfigFile
        if ($LASTEXITCODE -eq 0) {
            break
        }
        Write-Host "登录失败。30秒后再次进行尝试……" -ForegroundColor Red
        Start-Sleep -Seconds 30
    }

    while (Test-Connection -TargetName www.baidu.com, www.bilibili.com, www.bing.com -IPv4) {
        Write-Host (Get-Date).ToString(): "网络已连接，5分钟后再次检测。" -ForegroundColor Green
        Start-Sleep -Duration (New-TimeSpan -Minutes 5)
    }

    Write-Host (Get-Date).ToString(): "网络断开。正在重新连接……" -ForegroundColor Red
}
