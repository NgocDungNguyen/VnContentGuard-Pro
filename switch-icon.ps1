# ============================================================================
# VnContentGuard Pro - Icon Switcher Script
# Easily switch between Production, Test, and Dev icons
# ============================================================================

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("prod", "test", "dev")]
    [string]$Mode
)

$extensionPath = "c:\Users\LucyS\Tox\extension"
$manifestPath = "$extensionPath\manifest.json"
$iconsPath = "$extensionPath\icons"

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host "="*78 -ForegroundColor Cyan
Write-Host "  VnContentGuard Pro - Icon Switcher" -ForegroundColor White
Write-Host "="*80 -ForegroundColor Cyan
Write-Host ""

# Check if icon files exist
$prodIcon = "$iconsPath\icon-128.png"
$testIcon = "$iconsPath\icon-test-128.png"
$devIcon = "$iconsPath\icon-dev-128.png"

if (-not (Test-Path $prodIcon)) {
    Write-Host "❌ Error: Production icon not found!" -ForegroundColor Red
    Write-Host "   Expected: $prodIcon" -ForegroundColor Yellow
    Write-Host "   Please save the 'Pro' icon (gold) as icon-128.png" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $testIcon)) {
    Write-Host "❌ Error: Test icon not found!" -ForegroundColor Red
    Write-Host "   Expected: $testIcon" -ForegroundColor Yellow
    Write-Host "   Please save the 'Test' icon (yellow) as icon-test-128.png" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $devIcon)) {
    Write-Host "❌ Error: Dev icon not found!" -ForegroundColor Red
    Write-Host "   Expected: $devIcon" -ForegroundColor Yellow
    Write-Host "   Please save the 'Dev' icon (green) as icon-dev-128.png" -ForegroundColor Yellow
    exit 1
}

# Determine which icon to use
$iconFile = switch ($Mode) {
    "prod" { "icon-128.png"; $displayName = "Production (Pro - Gold)"; $color = "Yellow" }
    "test" { "icon-test-128.png"; $displayName = "Testing (Test - Yellow)"; $color = "Cyan" }
    "dev"  { "icon-dev-128.png"; $displayName = "Development (Dev - Green)"; $color = "Green" }
}

Write-Host "🔄 Switching to: " -NoNewline
Write-Host $displayName -ForegroundColor $color
Write-Host ""

# Read manifest
$manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json

# Update icon paths
$manifest.icons = @{
    "16" = "icons/$iconFile"
    "32" = "icons/$iconFile"
    "48" = "icons/$iconFile"
    "128" = "icons/$iconFile"
}

$manifest.action.default_icon = @{
    "16" = "icons/$iconFile"
    "32" = "icons/$iconFile"
    "48" = "icons/$iconFile"
    "128" = "icons/$iconFile"
}

# Update extension name to reflect mode
switch ($Mode) {
    "prod" { $manifest.name = "VnContentGuard Pro" }
    "test" { $manifest.name = "VnContentGuard Test" }
    "dev"  { $manifest.name = "VnContentGuard Dev" }
}

# Save manifest
$manifest | ConvertTo-Json -Depth 10 | Set-Content $manifestPath

Write-Host "✅ Icon switched successfully!" -ForegroundColor Green
Write-Host "✅ Extension name updated to: " -NoNewline
Write-Host $manifest.name -ForegroundColor $color
Write-Host ""
Write-Host "📋 Next Steps:" -ForegroundColor Cyan
Write-Host "   1. Go to chrome://extensions/" -ForegroundColor Gray
Write-Host "   2. Click the reload icon under VnContentGuard" -ForegroundColor Gray
Write-Host "   3. The new icon will appear!" -ForegroundColor Gray
Write-Host ""
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host "="*78 -ForegroundColor Cyan
