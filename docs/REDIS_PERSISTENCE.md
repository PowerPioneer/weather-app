# Redis Persistence Guide

## Overview

Redis persistence determines what happens to cached data when Redis restarts. This guide explains the options and why we chose RDB snapshots for this app.

---

## Persistence Methods

### 1. RDB (Redis Database) Snapshots ✅ **RECOMMENDED**

**What it does:**
- Takes periodic "snapshots" of all data in memory
- Saves to a single file: `/var/lib/redis/dump.rdb`
- Compact binary format

**Configuration (already set in DEPLOYMENT.md):**
```ini
save 900 1      # Save after 15 min if 1+ keys changed
save 300 10     # Save after 5 min if 10+ keys changed  
save 60 10000   # Save after 1 min if 10,000+ keys changed
```

**How it works:**
1. Redis forks a child process
2. Child writes current data to temporary RDB file
3. When done, replaces old RDB file with new one
4. Parent process continues serving requests

**Pros:**
- ✅ Fast restarts (single file to load)
- ✅ Low performance overhead (only periodic saves)
- ✅ Small file size (compressed binary)
- ✅ Perfect for static data (like climate data)
- ✅ Easy backups (just copy dump.rdb)

**Cons:**
- ❌ Can lose up to 15 minutes of data if server crashes
- ❌ Uses extra memory during fork (copy-on-write)

**Best for:** Applications with mostly static data where losing recent cache entries is acceptable.

---

### 2. AOF (Append-Only File)

**What it does:**
- Logs every write command to a file: `/var/lib/redis/appendonly.aof`
- Like a database transaction log
- Replays commands on restart to rebuild data

**Configuration:**
```ini
appendonly yes
appendfsync everysec  # Sync to disk every second
```

**How it works:**
1. Every SET/HSET/etc command is appended to AOF file
2. On restart, Redis replays all commands sequentially
3. Periodically rewrites AOF to compact it

**Pros:**
- ✅ Very durable (can lose max 1 second of data)
- ✅ Can recover from file corruption (just remove bad commands)
- ✅ Good for frequently changing data

**Cons:**
- ❌ Slower restarts (must replay all commands)
- ❌ Larger files than RDB
- ❌ Slight performance overhead (disk writes)
- ❌ AOF rewrite can temporarily use extra memory

**Best for:** Applications where data loss is unacceptable and data changes frequently.

---

### 3. Both RDB + AOF (Hybrid)

**What it does:**
- Enables both persistence methods
- On restart, Redis prefers AOF (more durable)

**Pros:**
- ✅ Maximum durability
- ✅ RDB provides backup if AOF corrupts

**Cons:**
- ❌ Overhead of both methods
- ❌ More complex to manage

**Best for:** Mission-critical applications where data must never be lost.

---

### 4. No Persistence (Ephemeral Cache) ⚡

**What it does:**
- Redis runs in memory only
- All data lost on restart

**Configuration:**
```ini
save ""
appendonly no
```

**Pros:**
- ✅ Maximum performance (no disk I/O)
- ✅ Simplest setup
- ✅ Fine if data can be regenerated

**Cons:**
- ❌ Cold start after every restart
- ❌ All cache entries lost

**Best for:** Pure caching where source data is always available and cold starts are acceptable.

---

## Why We Chose RDB for This App

### Reasoning:

1. **Static Data**: Climate data doesn't change after processing
2. **Reproducible**: All cached data can be regenerated from GeoJSON/GeoTIFF files
3. **Fast Restarts**: RDB loads much faster than AOF
4. **Low Overhead**: Periodic snapshots don't impact request handling
5. **Acceptable Data Loss**: Losing 15 minutes of cache means some requests hit disk - not critical

### Alternative: No Persistence

You could also disable persistence entirely and treat Redis as a pure cache:

**Pros:**
- Slightly better performance
- Simpler configuration
- No disk space used

**Cons:**
- Cold start after every Redis restart (~30 seconds to warm cache)
- More frequent disk hits until cache rebuilds

**To disable persistence:**
```bash
# Edit /etc/redis/redis.conf
save ""
appendonly no

# Restart Redis
sudo systemctl restart redis-server
```

---

## Monitoring Persistence

### Check if RDB is working:

```bash
# Last save time
redis-cli LASTSAVE

# Trigger manual save
redis-cli BGSAVE

# Check RDB file
ls -lh /var/lib/redis/dump.rdb
```

### View save statistics:

```bash
redis-cli INFO persistence
```

Key metrics:
- `rdb_last_save_time`: Unix timestamp of last successful save
- `rdb_changes_since_last_save`: Number of changes since last save
- `rdb_last_bgsave_status`: ok/err

---

## Backup Strategy

### Automatic Backups:

Create a cron job to copy RDB file daily:

```bash
# Edit crontab
sudo crontab -e

# Add daily backup at 3 AM
0 3 * * * cp /var/lib/redis/dump.rdb /backup/redis-$(date +\%Y\%m\%d).rdb

# Keep only last 7 days
0 4 * * * find /backup -name "redis-*.rdb" -mtime +7 -delete
```

### Manual Backup:

```bash
# Trigger save
redis-cli BGSAVE

# Wait for completion
redis-cli INFO persistence | grep rdb_bgsave_in_progress
# Should show: rdb_bgsave_in_progress:0

# Copy file
sudo cp /var/lib/redis/dump.rdb ~/redis-backup-$(date +%Y%m%d).rdb
```

### Restore from Backup:

```bash
# Stop Redis
sudo systemctl stop redis-server

# Replace dump file
sudo cp /path/to/backup.rdb /var/lib/redis/dump.rdb
sudo chown redis:redis /var/lib/redis/dump.rdb

# Start Redis
sudo systemctl start redis-server

# Warm cache
cd /var/www/Where\ to\ go\ for\ great\ weather
source venv/bin/activate
python scripts/warm_cache.py
```

---

## Switching Persistence Methods

### From RDB to No Persistence:

```bash
# Edit config
sudo nano /etc/redis/redis.conf

# Disable RDB
save ""

# Disable AOF (if enabled)
appendonly no

# Restart
sudo systemctl restart redis-server
```

### From RDB to AOF:

```bash
# Edit config
sudo nano /etc/redis/redis.conf

# Enable AOF
appendonly yes
appendfsync everysec

# Optional: Keep RDB as backup
save 900 1

# Restart
sudo systemctl restart redis-server
```

---

## Conclusion

**For this weather app, RDB snapshots provide the best balance:**
- Fast performance
- Quick restarts
- Acceptable data loss (cache can rebuild)
- Simple management

**Choose no persistence if:**
- You prioritize maximum performance
- Cold starts are acceptable
- You have automated cache warming

**Choose AOF if:**
- You cache user-specific data
- Data loss is unacceptable
- You don't mind slower restarts
