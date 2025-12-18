# API Keys and Credentials

This folder contains sensitive API credentials and configuration. **These files should never be committed to git.**

## Setup Instructions

### 1. Create `config.py`

Copy the template and fill in your actual credentials:

```bash
cp config.example.py config.py
```

Then edit `config.py` and add your credentials:

```python
# CDS API Credentials (from https://cds.climate.copernicus.eu/)
# See: https://cds.climate.copernicus.eu/how-to-api
CDS_API_KEY = "YOUR_API_KEY"

# Flask Secret Key - Used for CSRF protection if forms are added
# Note: This app is currently read-only with no login/authentication
# Use any simple string (e.g., "dev-key" for development)
FLASK_SECRET_KEY = "dev-key"

# Weather API Key (if needed)
WEATHER_API_KEY = "your-weather-api-key-here"
```

### 2. Get CDS Credentials

1. Go to https://cds.climate.copernicus.eu/
2. Create a free account
3. Go to your profile settings
4. Copy your API Key (see https://cds.climate.copernicus.eu/how-to-api for details)
5. Add it to `config.py`

### 3. How Credentials are Used

- **CDS API Credentials**: Used by `scripts/download_era5_data.py` to download climate data
  - The `url: https://cds.climate.copernicus.eu/api/v2` is the endpoint (hardcoded in the script)
  - Your API_KEY is your authentication credential for that endpoint
- **Flask Secret Key**: Used for CSRF protection if forms are added in the future
  - Currently, this app is read-only with no login/authentication system
  - Not critical for the current deployment, but required by Flask if any form-based features are added
- **Weather API Key**: Reserved for future weather service integrations

## Files in This Folder

| File | Purpose | Status |
|------|---------|--------|
| `config.example.py` | Template for credentials | ✓ Tracked in git |
| `config.py` | Your actual credentials | ✗ Not tracked (in .gitignore) |
| `.gitkeep` | Ensures folder is tracked | ✓ Tracked in git |

## Security Best Practices

1. **Never commit** `config.py` - it contains secrets
2. **Never share** your CDS API credentials
3. **Use environment variables** in production instead of `config.py`:
   ```bash
   export CDS_API_KEY="your-key"
   export FLASK_SECRET_KEY="your-secret"
   ```
4. **Rotate keys regularly** if you suspect compromise
5. **Keep the example file updated** when adding new credentials

## Troubleshooting

### "CDS API key not configured"
- Verify your API key is correct in `config.py`
- Check that you've accepted the ERA5 license terms on the CDS website
- Try regenerating your key on the CDS website

### Connection Errors
- Check your internet connection
- Verify your credentials are correct
- Make sure you've accepted the license terms: https://cds.climate.copernicus.eu/
