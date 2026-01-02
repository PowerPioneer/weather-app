# Deployment Guide - Scaleway VPS

## Server Setup (One-time)

### 1. Initial Setup on VPS

```bash
# SSH into your VPS
ssh user@your-server-ip

# Clone repository
cd /var/www  # or your preferred location
git clone https://github.com/your-username/your-repo.git
cd "Where to go for great weather"

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install production dependencies
pip install -r requirements-server.txt
```

### 2. Configure Environment

```bash
# Create .env file from example
cp .env.example .env

# Edit .env with production settings
nano .env
```

Set these values in `.env`:
```bash
FLASK_ENV=production
FLASK_DEBUG=0
FLASK_SECRET_KEY=your-generated-secret-key-here
```

Generate a secure secret key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Install and Configure Redis

```bash
# Install Redis server
sudo apt update
sudo apt install redis-server

# Configure Redis for production
sudo nano /etc/redis/redis.conf
```

**Important Redis configuration changes:**

```ini
# Set max memory limit (e.g., 512MB for this app)
maxmemory 512mb

# Eviction policy when max memory reached (least recently used)
maxmemory-policy allkeys-lru

# Enable RDB snapshots for persistence
save 900 1      # Save after 15 min if 1+ keys changed
save 300 10     # Save after 5 min if 10+ keys changed  
save 60 10000   # Save after 1 min if 10000+ keys changed

# Set RDB file location
dir /var/lib/redis
dbfilename dump.rdb

# Optional: Disable AOF (we're using RDB)
appendonly no

# Bind to localhost only (security)
bind 127.0.0.1 ::1
```

**Start Redis:**
```bash
# Start Redis service
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Check status
sudo systemctl status redis-server

# Test connection
redis-cli ping
# Should return: PONG
```

### 4. Create Systemd Service

Create `/etc/systemd/system/weather-app.service`:

```ini
[Unit]
Description=Where to go for great weather Flask App
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/Where to go for great weather
Environment="PATH=/var/www/Where to go for great weather/venv/bin"
EnvironmentFile=/var/www/Where to go for great weather/.env
ExecStart=/var/www/Where to go for great weather/venv/bin/gunicorn \
    --workers 4 \
    --bind 0.0.0.0:5000 \
    --timeout 120 \
    --access-logfile /var/log/weather-app/access.log \
    --error-logfile /var/log/weather-app/error.log \
    app:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always

[Install]
WantedBy=multi-user.target
```

### 5. Create Log Directory

```bash
sudo mkdir -p /var/log/weather-app
sudo chown www-data:www-data /var/log/weather-app
```

### 6. Warm Redis Cache

```bash
# Pre-populate cache with GeoJSON files
source venv/bin/activate
python scripts/warm_cache.py
```

This loads all 24 GeoJSON files into Redis, eliminating cold-start delays.

### 7. Start Service

```bash
# Enable service to start on boot
sudo systemctl enable weather-app

# Start the service
sudo systemctl start weather-app

# Check status
sudo systemctl status weather-app
```

### 8. Configure Reverse Proxy (Optional but Recommended)

If using nginx as reverse proxy, create `/etc/nginx/sites-available/weather-app`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Increase timeout for large data requests
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
    }

    # Cache static files at nginx level
    location /static {
        alias /var/www/Where to go for great weather/static;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/weather-app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Deploying Updates (Git Pull Workflow)

### Method 1: Manual Deployment

```bash
# SSH into server
ssh user@your-server-ip

# Navigate to app directory
cd /var/www/Where\ to\ go\ for\ great\ weather

# Pull latest changes
git pull origin main

# Activate virtual environment if needed
source venv/bin/activate

# Install any new dependencies
pip install -r requirements-server.txt

# Restart the service
sudo systemctl restart weather-app

# Check status
sudo systemctl status weather-app

# Watch logs if needed
sudo journalctl -u weather-app -f
```

### Method 2: Deployment Script

Create `deploy.sh` in your project root:

```bash
#!/bin/bash
# Deployment script for weather app

set -e  # Exit on error

echo "🚀 Starting deployment..."

# Pull latest code
echo "📥 Pulling latest changes..."
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo "📦 Updating dependencies..."
pip install -r requirements-server.txt

# Warm cache if Redis is available
echo "🔥 Warming Redis cache..."
python scripts/warm_cache.py || echo "⚠️  Cache warming skipped (Redis not available)"

# Restart service
echo "🔄 Restarting service..."
sudo systemctl restart weather-app

# Check if service is running
if systemctl is-active --quiet weather-app; then
    echo "✅ Deployment successful! Service is running."
else
    echo "❌ Deployment failed! Service is not running."
    sudo systemctl status weather-app
    exit 1
fi

echo "✨ Deployment complete!"
```

Make it executable:
```bash
chmod +x deploy.sh
```

Then deploy with:
```bash
./deploy.sh
```

### Method 3: Zero-Downtime Deployment

For zero-downtime updates using gunicorn's graceful reload:

```bash
# Pull changes
git pull origin main

# Reload gunicorn workers gracefully (no restart needed)
sudo systemctl reload weather-app
```

This reloads workers one-by-one, maintaining service availability.

---

## Troubleshooting

### Check Service Status
```bash
sudo systemctl status weather-app
```

### View Logs
```bash
# Service logs
sudo journalctl -u weather-app -f

# Application logs
sudo tail -f /var/log/weather-app/error.log
sudo tail -f /var/log/weather-app/access.log
```

### Test Configuration
```bash
# Test gunicorn directly
cd /var/www/Where\ to\ go\ for\ great\ weather
source venv/bin/activate
gunicorn --bind 0.0.0.0:5000 app:app
```

### Permission Issues
```bash
# Fix ownership
sudo chown -R www-data:www-data /var/www/Where\ to\ go\ for\ great\ weather
```

### Redis Issues

**Check Redis status:**
```bash
sudo systemctl status redis-server
redis-cli ping  # Should return PONG
```

**View Redis logs:**
```bash
sudo tail -f /var/log/redis/redis-server.log
```

**Check cache contents:**
```bash
# Connect to Redis CLI
redis-cli

# List all weather cache keys
KEYS weather:*

# Get cache stats
INFO stats
INFO memory

# Count total keys
DBSIZE

# View specific cached data
GET "weather:geojson:country:month:1"

# Clear all cache (if needed)
FLUSHDB

# Exit
exit
```

**Monitor Redis memory usage:**
```bash
redis-cli INFO memory | grep used_memory_human
```

**Restart Redis:**
```bash
sudo systemctl restart redis-server
```

**After Redis restart, warm cache:**
```bash
cd /var/www/Where\ to\ go\ for\ great\ weather
source venv/bin/activate
python scripts/warm_cache.py
```

---

## Monitoring & Maintenance

### Cache Statistics

Check cache performance via API:
```bash
curl http://localhost:5000/api/cache/stats
```

Returns cache hit/miss rates and memory usage (Redis only).

### Redis Persistence

**RDB snapshots** are configured to save automatically:
- Every 15 minutes if 1+ keys changed
- Every 5 minutes if 10+ keys changed
- Every 1 minute if 10,000+ keys changed

**Backup location:** `/var/lib/redis/dump.rdb`

**Manual backup:**
```bash
# Trigger immediate snapshot
redis-cli BGSAVE

# Copy backup file
sudo cp /var/lib/redis/dump.rdb /path/to/backup/
```

**Restore from backup:**
```bash
# Stop Redis
sudo systemctl stop redis-server

# Replace dump file
sudo cp /path/to/backup/dump.rdb /var/lib/redis/dump.rdb
sudo chown redis:redis /var/lib/redis/dump.rdb

# Start Redis
sudo systemctl start redis-server
```

---

## Local Development

On your PC, the app automatically runs in development mode:

```bash
# Just run normally
python app.py
```

The app detects you're on localhost and enables:
- Debug mode
- Auto-reload on code changes
- No static file caching
- Detailed error pages
- **Optional Redis**: Set `REDIS_ENABLED=0` to disable Redis locally

No need to set environment variables locally!

---

## Environment Detection

The app automatically detects the environment:

1. **Explicit**: Set `FLASK_ENV=production` in `.env` on server
2. **Auto-detect**: Checks hostname (localhost/desktop = development)
3. **Default**: Production (safe default)

Debug mode follows environment unless explicitly set with `FLASK_DEBUG`.
