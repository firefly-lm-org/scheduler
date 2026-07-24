$ErrorActionPreference = "Continue"
$env:PYTHONIOENCODING = "utf-8"
$env:FIREFLY_HOME = "D:\firefly-scheduler\_e2e\home"
$env:FIREFLY_E2E = "1"
$CLIENT = "D:\firefly-client\firefly-client"
$SCHED = "http://localhost:8000"
$EHOME = "D:\firefly-scheduler\_e2e\home"

$ts = [int](Get-Date -UFormat %s)
$USER = "e2e_$ts"
$PWD = "e2e_pass_123"

Set-Location $CLIENT

Write-Host "=== 1) register ==="
python3 -m app.main register --username $USER --password $PWD *>1 | Out-Null

Write-Host "=== 2) node-register ==="
python3 -m app.main node-register e2e-pc *>1 | Out-Null

Write-Host "=== 3) start client in background ==="
$log = "$EHOME\client.log"
Set-Content -Path $log -Value "" -Encoding UTF8
Start-Process -FilePath "python3" -ArgumentList "-m","app.main","start" -WorkingDirectory $CLIENT -RedirectStandardOutput $log -RedirectStandardError "$EHOME\client.err" -NoNewWindow
# 等待心跳上线（HEARTBEAT_INTERVAL=30s），多等几秒
Start-Sleep -Seconds 38

Write-Host "=== 4) create task (fresh token from config.json) ==="
$tok = (Get-Content "$EHOME\config.json" | ConvertFrom-Json).access_token
$file = "$EHOME\sample_package.zip"
$resp = curl.exe -s -i -H "Authorization: Bearer $tok" -F "name=e2e-task" -F "level=1" -F "base_contribution=10" -F "timeout_sec=3600" -F "max_retries=3" -F "config={\"lr\":2e-4}" -F "package=@$file;type=application/zip" "$SCHED/api/v1/admin/tasks" 2>&1 | Select-String -Pattern "HTTP|task_id|message|detail" | ForEach-Object { "  $($_.Line)" }

Write-Host "=== 5) wait for claim->download->train->submit ==="
$deadline = (Get-Date).AddSeconds(50)
while ((Get-Date) -lt $deadline) {
    $c = Get-Content $log -Encoding UTF8 -ErrorAction SilentlyContinue -Raw
    if ($c -match "uploaded" -or $c -match "submitted" -or $c -match "completed" -or $c -match "result" -or $c -match "领取成功") {
        Write-Host "  [client finished a task cycle]"
        break
    }
    Start-Sleep -Seconds 3
}

Write-Host "=== 6) client.log tail ==="
Get-Content $log -Encoding UTF8 -Tail 45

Write-Host "=== 7) admin stats ==="
curl.exe -s -H "Authorization: Bearer $tok" "$SCHED/api/v1/admin/stats"
