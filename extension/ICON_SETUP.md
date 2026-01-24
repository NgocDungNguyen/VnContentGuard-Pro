# Icon Setup Instructions

## Save the 3 Icon Files

Please save the 3 PNG images you provided to these locations:

1. **Production Icon (Pro - Gold "Pro")**
   - Save as: `c:\Users\LucyS\Tox\extension\icons\icon-128.png`
   - This is the production/published extension icon

2. **Developer Mode Icon (Test - Yellow "Test")**
   - Save as: `c:\Users\LucyS\Tox\extension\icons\icon-test-128.png`
   - Use this when testing in developer mode

3. **Local Testing Icon (Dev - Green "Dev")**
   - Save as: `c:\Users\LucyS\Tox\extension\icons\icon-dev-128.png`
   - Use this when testing with local API server

## Quick Setup Script

After saving the images, run this PowerShell script to set up different sizes:

```powershell
cd c:\Users\LucyS\Tox\extension\icons

# You'll need to manually create 16x16, 32x32, 48x48 versions
# Or use online tools like https://www.iloveimg.com/resize-image
# For now, we'll use the 128x128 for all sizes (Chrome will auto-resize)
```

## Current Configuration

The manifest.json will use:
- **Default (Production)**: `icon-128.png` (Pro version with gold)
- **Testing**: Manually switch icons in manifest when needed

## Files Created
- ✅ `extension/icons/` folder created
- ⏳ Waiting for you to save the 3 PNG files
