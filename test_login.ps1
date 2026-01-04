# Test Login API

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Test Login with Email" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$emailBody = @{
    email = "shehneh.m@gmail.com"
    password = "123456"
    auth_method = "email"
} | ConvertTo-Json

try {
    $emailResponse = Invoke-RestMethod -Uri "http://localhost:5000/api/login" -Method Post -Body $emailBody -ContentType "application/json"
    Write-Host "SUCCESS: Email login worked!" -ForegroundColor Green
    Write-Host ($emailResponse | ConvertTo-Json -Depth 5) -ForegroundColor Green
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Test Login with Phone" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$phoneBody = @{
    phone = "09961979369"
    password = "123456"
    auth_method = "phone"
} | ConvertTo-Json

try {
    $phoneResponse = Invoke-RestMethod -Uri "http://localhost:5000/api/login" -Method Post -Body $phoneBody -ContentType "application/json"
    Write-Host "SUCCESS: Phone login worked!" -ForegroundColor Green
    Write-Host ($phoneResponse | ConvertTo-Json -Depth 5) -ForegroundColor Green
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
}
