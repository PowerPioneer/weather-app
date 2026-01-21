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
# Redirect www to non-www (for SEO canonical URL)
server {
    listen 80;
    listen 443 ssl;
    server_name www.wheretogoforgreatweather.com;
    
    # SSL certificates (if using https)
    # ssl_certificate /etc/letsencrypt/live/wheretogoforgreatweather.com/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/wheretogoforgreatweather.com/privkey.pem;
    
    # 301 permanent redirect from www to non-www
    return 301 $scheme://wheretogoforgreatweather.com$request_uri;
}

# Main server block (non-www)
server {
    listen 80;
    server_name wheretogoforgreatweather.com;
    
    # Uncomment for HTTPS:
    # listen 443 ssl;
    # ssl_certificate /etc/letsencrypt/live/wheretogoforgreatweather.com/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/wheretogoforgreatweather.com/privkey.pem;

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

**Important for SEO:** The configuration above redirects all `www.` traffic to the non-www version (e.g., `www.wheretogoforgreatweather.com` → `wheretogoforgreatweather.com`). This prevents duplicate content issues in Google Search Console. The canonical URL tags in the HTML templates will also point to the non-www version.

---

## Deploying Updates (Git Pull Workflow)

### Quick Deployment with deploy.sh

The easiest way to deploy updates is using the included `deploy.sh` script:

```bash
# SSH into server
ssh user@your-server-ip

# Navigate to app directory
cd /var/www/Where\ to\ go\ for\ great\ weather

# Run deployment script
./deploy.sh
```

The script will:
1. Pull latest code from git
2. Install/update dependencies
3. Warm Redis cache
4. Restart the service
5. Verify the service is running

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

**Note:** The `deploy.sh` script (Method 2 below) automates all these steps.

### Method 2: Using the Deployment Script

The repository includes a `deploy.sh` script that's already been created. First time setup:

```bash
# SSH into server
ssh user@your-server-ip

# Navigate to app directory
cd /var/www/Where\ to\ go\ for\ great\ weather

# Make the script executable (only needed once)
chmod +x deploy.sh
```

Then for all future deployments:

```bash
./deploy.sh
```

The script handles everything automatically:
- Pulls latest code from git
- Activates virtual environment
- Installs/updates dependencies
- Warms Redis cache (if available)
- Restarts the service
- Verifies the service is running
- Shows deployment status

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
