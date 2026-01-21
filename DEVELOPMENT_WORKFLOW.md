# Development & Deployment Workflow

## Huidige Setup Status: ✅ Klaar voor Gebruik

Je app is correct geconfigureerd met automatische environment detection.

---

## 🏠 Development Workflow (Lokaal)

### 1. Code wijzigingen maken
```powershell
# Work in: c:\Projects\Where to go for great weather
# Edit files in VSCode
```

De app detecteert automatisch development mode op je lokale machine:
- ✅ Debug mode = ON
- ✅ Auto-reload bij code changes
- ✅ Gedetailleerde error pages
- ✅ Redis optioneel (fallback naar memory cache)

### 2. Lokaal testen
```powershell
# Start Flask app in venv
.\venv\Scripts\python.exe app.py

# App draait op http://127.0.0.1:8080
# Test je wijzigingen in browser
```

### 3. Commit naar Git
```powershell
# Stage je wijzigingen
git add .

# Commit met duidelijke message
git commit -m "feat: beschrijving van je wijziging"

# Push naar GitHub
git push origin main
```

---

## 🚀 Production Deployment (Server)

### Eenmalige Server Setup (al gedaan)

Je server heeft al:
- ✅ Git repository gecloned
- ✅ Virtual environment met dependencies
- ✅ Systemd service (weather-app)
- ✅ Nginx reverse proxy
- ✅ Redis cache (optioneel)
- ✅ deploy.sh script

### Deploy Nieuwe Code (Herhaalbaar Proces)

**SSH naar je server:**
```bash
ssh user@your-server-ip
cd /var/www/Where\ to\ go\ for\ great\ weather
```

**Optie 1: Gebruik deploy.sh (Aanbevolen)**
```bash
./deploy.sh
```
Het script doet automatisch:
1. `git pull origin main` - Haalt laatste code op
2. `pip install -r requirements-server.txt` - Update dependencies
3. `python scripts/warm_cache.py` - Warmt Redis cache op
4. `sudo systemctl restart weather-app` - Herstart service
5. Verificatie dat service draait

**Optie 2: Handmatige Deploy**
```bash
git pull origin main
source venv/bin/activate
pip install -r requirements-server.txt
python scripts/warm_cache.py  # Optioneel maar aanbevolen
sudo systemctl restart weather-app
sudo systemctl status weather-app
```

---

## 🔧 Environment Configuratie

### Development (Automatisch)
Het systeem detecteert development wanneer:
- Hostname bevat: `localhost`, `local`, `dev`, `desktop`, `laptop`
- OF `FLASK_ENV=development` is gezet

Settings:
- `DEBUG=True`
- Redis optioneel
- Geen static file caching

### Production (Automatisch)
Het systeem detecteert production op je server.

Settings:
- `DEBUG=False`
- Redis aanbevolen
- Static file caching enabled
- Gunicorn WSGI server

**Server Environment File (optioneel):**
Normaal gesproken niet nodig door auto-detection, maar je kunt `/var/www/Where to go for great weather/.env` maken:

```bash
FLASK_ENV=production
FLASK_DEBUG=0
FLASK_SECRET_KEY=your-generated-secret-key-here
```

---

## 📋 Deployment Checklist

### Voordat je pushed:
- [ ] Code werkt lokaal (test op http://127.0.0.1:8080)
- [ ] Geen syntax errors
- [ ] Git commit message is duidelijk

### Na git push:
- [ ] SSH naar server
- [ ] Run `./deploy.sh`
- [ ] Verificeer service draait: `sudo systemctl status weather-app`
- [ ] Test website in browser
- [ ] Check logs indien nodig: `sudo journalctl -u weather-app -f`

---

## 🚨 Troubleshooting

### Als deploy.sh faalt:

**1. Check logs:**
```bash
sudo journalctl -u weather-app -n 50
```

**2. Check service status:**
```bash
sudo systemctl status weather-app
```

**3. Manual restart:**
```bash
sudo systemctl restart weather-app
```

**4. Check nginx:**
```bash
sudo nginx -t
sudo systemctl status nginx
```

### Als Redis niet werkt:
De app werkt ook zonder Redis (fallback naar memory cache).

**Check Redis:**
```bash
sudo systemctl status redis-server
redis-cli ping  # Should return PONG
```

---

## 🔄 Complete Development Cycle

```
1. LOKAAL: Edit code in VSCode
         ↓
2. LOKAAL: Test met .\venv\Scripts\python.exe app.py
         ↓
3. LOKAAL: git add . && git commit -m "message"
         ↓
4. LOKAAL: git push origin main
         ↓
5. SERVER: SSH naar server
         ↓
6. SERVER: ./deploy.sh
         ↓
7. BROWSER: Test productie site
```

---

## ✅ Je Bent Klaar!

De workflow is compleet ingesteld:
- ✅ Development mode automatisch lokaal
- ✅ Production mode automatisch op server
- ✅ deploy.sh voor makkelijke deployments
- ✅ Redis cache warming geïntegreerd
- ✅ Zero-downtime deployment met systemd

**Next Steps:**
1. Test de workflow: maak een kleine wijziging lokaal
2. Push naar git
3. Run `./deploy.sh` op de server
4. Verificeer dat alles werkt

De SEO fixes (canonical tags + www redirect) zijn nu ook onderdeel van deze workflow! 🎉
