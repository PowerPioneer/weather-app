# Where to go for great weather - Bug Fixes

## Map Controls Redesign (13 Feb 2026)

### Plan

- [x] Replace legacy sidebar/toggle controls with a 3-button map control stack (Month, Display Mode, Personal Preferences) for both desktop and mobile
- [x] Move month selection into Button 1 as a 12-month grid and remove duplicate month selector locations
- [x] Keep Button 2 with mode choices: My Preferences, Temp, Rain, Safety, Sun
- [x] Keep Button 3 with existing preference controls (temp/rain/sun/safety/unit) and Clear Cache button
- [x] Implement single-open panel behavior (opening one panel closes the others)
- [x] Ensure controls do not overlap: below desktop zoom controls, and away from mobile legend area
- [x] Ensure open panel content remains visible while ad is shown
- [x] Regenerate minified assets and run targeted validation

### Review (13 Feb 2026)

- Replaced the old climate sidebar/toggle architecture with a unified 3-button control stack on top-left of the map for desktop and mobile
- Added separate month, display mode, and personal preference panels with single-open behavior and click-outside/Escape close handling
- Moved month selection to a 12-month grid; preserved existing display modes including My Preferences and preserved all preference controls plus Clear Cache
- Added responsive panel sizing/positioning so desktop controls are below zoom controls and mobile panel content remains visible above the bottom ad
- Rebuilt production assets with `scripts/minify_assets.py` (`static/script.min.js`, `static/style.min.css`)

## Cache Warming Deploy Check (11 Feb 2026)

### Plan

- [x] Confirm deploy.sh currently performs cache warming via scripts/warm_cache.py
- [x] If missing or incomplete, add a deploy step to warm the cache
- [x] Update review section with the outcome and any changes made

### Review (11 Feb 2026)

- deploy.sh already warms cache via scripts/warm_cache.py inside a guarded block; no changes needed
- Warming step is non-blocking under set -e (wrapped in conditional), so deploy flow is safe if Redis is down
- No code changes required; plan closed

## Console Errors Investigation - NIEUWE FIX (26 Jan 2026)

### Problem

Developer console toont TWEE warnings over Leaflet library:

1. **Preload Credentials Mismatch**: "A preload for 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js' is found, but is not used because the request credentials mode does not match."
2. **Unused Preload (2x)**: "The resource https://unpkg.com/leaflet@1.9.4/dist/leaflet.js was preloaded using link preload but not used within a few seconds from the window's load event."

### Analysis - NIEUWE INZICHTEN

❌ **Vorige fix was VERKEERD** - we hebben crossorigin juist VERWIJDERD, maar dat was niet de oplossing!

**Correcte Root Cause:**

- Externe CDN resources (unpkg.com) zijn **CORS resources**
- Zowel preload als script tag hebben `crossorigin="anonymous"` NODIG
- De credentials mode moet matchen tussen preload en het daadwerkelijke script
- ZONDER crossorigin attribuut proberen ze verschillende credential modes te gebruiken

### Correcte Oplossing (volgens MDN en browser best practices)

Voeg `crossorigin="anonymous"` toe aan:

1. De Leaflet JS preload link (regel 17)
2. Het Leaflet JS script tag (regel 316)

Dit zorgt ervoor dat beide dezelfde CORS credentials mode gebruiken.

### Todo Items

- [x] 1. Voeg `crossorigin="anonymous"` toe aan Leaflet JS preload (regel 17)
- [x] 2. Voeg `crossorigin="anonymous"` toe aan Leaflet JS script tag (regel 316)
- [x] 3. Test in browser console of beide warnings verdwenen zijn

### Implementatie

✅ **Wijzigingen toegepast:**

- Regel 17: `<link rel="preload" ... crossorigin="anonymous">` toegevoegd
- Regel 316: `<script defer ... crossorigin="anonymous"></script>` toegevoegd

**Waarom dit werkt:**

- Externe CDN resources (unpkg.com) zijn CORS resources
- Browser vereist dat preload en script dezelfde credentials mode gebruiken
- `crossorigin="anonymous"` betekent: geen credentials (cookies, auth) worden meegestuurd
- Nu matchen de credentials modes en wordt de preload correct gebruikt

**Resultaat:**

- ✅ Credentials mismatch warning verdwijnt
- ✅ Unused preload warning verdwijnt
- ✅ Browser kan Leaflet.js nu correct preloaden voor betere performance

---

## OUDE Console Errors Investigation (22 Jan 2026) - SUPERSEDED

### Changes (VERKEERDE FIX)

✅ Removed `crossorigin` attributes from:

- Leaflet JS preload (line 17)
- Preconnect hints for unpkg.com, cdn.jsdelivr.net, app.enzuzo.com (lines 10-12)
- Leaflet CSS preload (line 57)

**NOTE: Deze fix was incorrect - we moeten crossorigin juist TOEVOEGEN, niet verwijderen!**

---

## Google Search Console SEO Fixes (21 Jan 2026)

### Probleem

Google Search Console meldt:

- "Page with redirect" (2 pages)
- "Duplicate without user-selected canonical" (1 page)

De site is bereikbaar via beide:

- http://wheretogoforgreatweather.com/
- http://www.wheretogoforgreatweather.com/

Dit veroorzaakt duplicate content issues.

### Oplossing

1. Canonical URL tags toevoegen aan alle HTML templates
2. Nginx configuratie voor www → non-www redirect (301)
3. Kies non-www als canonical (wheretogoforgreatweather.com)

### Todo Items

- [x] 1. Voeg canonical URL tags toe aan alle HTML templates (index, about, privacy, terms, cookies)
- [x] 2. Voeg Flask helper functie toe voor canonical URL generation
- [x] 3. Update DEPLOYMENT.md met nginx configuratie voor www redirect
- [x] 4. Maak deploy.sh script met cache warming

### Wijzigingen Gemaakt

#### 1. Flask Backend (`app/routes.py`)

- Nieuwe `get_canonical_url()` helper functie die automatisch non-www URL genereert
- Alle 5 routes updaten om `canonical_url` door te geven aan templates

#### 2. HTML Templates (5 bestanden)

- `<link rel="canonical">` tag toegevoegd aan alle templates:
  - index.html
  - about.html
  - privacy.html
  - terms.html
  - cookies.html

#### 3. Deployment Script (`deploy.sh`)

- Nieuw bash script voor geautomatiseerde deployment
- Bevat: git pull, pip install, cache warming, service restart, status check

#### 4. Nginx Configuratie (`DEPLOYMENT.md`)

- Toegevoegd: www → non-www redirect server block (301)
- Hoofdserver block voor non-www domein
- Instructies voor beide HTTP en HTTPS

### Server Acties (Eenmalig uit te voeren)

Na git pull op de server:

1. **Maak deploy.sh executable:**

   ```bash
   chmod +x deploy.sh
   ```

2. **Update nginx configuratie:**
   - Bewerk `/etc/nginx/sites-available/weather-app`
   - Voeg www redirect block toe (zie DEPLOYMENT.md)
   - Test en herlaad nginx:
     ```bash
     sudo nginx -t
     sudo systemctl reload nginx
     ```

3. **Deploy de code wijzigingen:**
   ```bash
   ./deploy.sh
   ```

### Verwachte Resultaten

✅ Canonical tags in alle pagina's (inspect source)
✅ www.wheretogoforgreatweather.com → wheretogoforgreatweather.com (301 redirect)
✅ Google Search Console ziet één canonical versie
✅ "Page with redirect" en "Duplicate content" warnings verdwijnen (na 1-2 weken)

---

## Current Issues (November 30, 2025)

### Issue 1: Map Projection Offset (Data appearing north of actual location)

**Root Cause:** Half-pixel offset issue in grid sampling. The code samples N points using `linspace(north, south, resolution)` which places the first sample exactly at the north edge. When drawn on canvas, each pixel represents a cell/area (not a point), creating a half-pixel northward shift.

**Fix:** Adjust sampling to sample at pixel CENTERS rather than edges. Instead of sampling from `north` to `south`, sample from `north - half_pixel` to `south + half_pixel`.

### Issue 2: Not all variables showing on map

**Status:** Need to verify. Backend data loading confirmed working for all variables (tmax, prec, srad). Investigating frontend layer switching.

---

## Todo Items

- [ ] 1. Fix the half-pixel offset in `data_loader.py` - adjust latitude/longitude sampling to use pixel centers
- [ ] 2. Verify all three layers (temperature, sunshine, rainfall) display correctly
- [ ] 3. Test with user feedback on the map

---

## Nieuwe Taak: Land en Provincie/Stad toevoegen (30 Nov 2025)

- [x] 1. Voeg reverse geocoding functie toe in `script.js` (Nominatim API)
- [x] 2. Update `onMapClick` om land en provincie/stad op te halen
- [x] 3. Update HTML in `index.html` om locatie-info te tonen

### Samenvatting wijzigingen:

- **`templates/index.html`**: Nieuw `locationDetails` div toegevoegd met elementen voor land en provincie/stad
- **`static/script.js`**: Nieuwe `fetchLocationName()` functie die Nominatim reverse geocoding API aanroept om land en provincie/stad op te halen wanneer gebruiker op de kaart klikt

---

## Review Section

(To be completed after fixes)

- After: 2 selectable variables (all with real data)

✅ **Files Modified:** 2 files

- templates/index.html
- static/script.js

✅ **Testing Results:**

- Server started successfully
- UI loaded without errors
- Only "Temperatuur" and "Regenval" checkboxes visible
- No JavaScript console errors

✅ **Data Alignment:**

- Temperatuur (tmin/tmax) ✅ Available in ERA5
- Regenval (prec) ✅ Available in ERA5
- Zonuren (sunshine hours) ✅ Available in CRU
- Luchtvochtigheid ❌ Removed (not available)

✅ **Code Quality:** Minimal, focused changes - no unnecessary refactoring

---

## Province-Level Data Aggregation - Phase 1 (December 10, 2025)

### Task: Download and Prepare Province Boundaries

#### Plan:

1. **Install required dependencies** (geopandas, rasterstats)
2. **Create download script** (`scripts/download_province_boundaries.py`)
   - Download Natural Earth Admin-1 data (states/provinces)
   - Extract and verify shapefile
   - Convert to GeoJSON for web use
   - Generate metadata (province count, coverage)
3. **Test the script** to ensure boundaries download correctly
4. **Document** the data structure and next steps

#### Todo Items:

- [x] 1. Add geopandas and rasterstats to requirements.txt
- [x] 2. Create download_province_boundaries.py script
- [x] 3. Create data/provinces/ directory structure
- [x] 4. Run script to download Natural Earth Admin-1 boundaries
- [x] 5. Verify downloaded files (shapefile and GeoJSON)
- [x] 6. Document province data structure in metadata

#### Completion Summary (December 10, 2025):

✅ **Successfully completed all Phase 1 tasks**

**Files Created:**

- `requirements.txt` - Added geopandas>=0.14.0, rasterstats>=0.19.0, shapely>=2.0.0
- `scripts/download_province_boundaries.py` - Download and processing script
- `data/provinces/ne_10m_admin_1_states_provinces.shp` - Shapefile (+ .dbf, .prj, .shx, .cpg)
- `data/provinces/provinces.geojson` - Web-ready GeoJSON (17.34 MB)
- `data/provinces/metadata.json` - Province metadata

**Data Summary:**

- **Source:** Natural Earth Admin-1 (Public Domain ✅)
- **License:** Public Domain - Commercial use allowed ✅
- **Total Provinces:** 4,596 provinces/states worldwide
- **Total Countries:** 253 countries
- **Coverage:** Global (-90°S to 83.63°N, -180°W to 180°E)
- **Format:** Both Shapefile (processing) and GeoJSON (web display)

**Available Attributes:**

- Province/state name and alternative names
- Country name and ISO codes
- Province type (State, Province, Region, etc.)
- Centroid coordinates (latitude, longitude)
- Geometry (polygon boundaries)

**Next Phase:** Build aggregation script to compute climate statistics per province

#### Expected Outputs:

- `data/provinces/ne_10m_admin_1_states_provinces.shp` (and related files)
- `data/provinces/provinces.geojson` (web-ready format)
- `data/provinces/metadata.json` (province count, attributes, coverage info)

#### Next Steps (Future Phases):

- Phase 2: Build aggregation script to compute provincial statistics
- Phase 3: Update frontend to display provincial view
- Phase 4: Pre-compute all provincial data for 12 months

---

## Province-Level Data Aggregation - Phase 2 (December 10, 2025)

### Task: Aggregate Climate Data Per Province & Update Frontend

#### Completed:

1. ✅ **Created aggregation script** (`scripts/aggregate_province_data.py`)
   - Processes all ERA5 (tmin, tmax, prec) and CRU (sunhours) data
   - Computes province-level averages using zonal statistics
   - Generates derived metrics (temp_avg, overall_score)
   - Outputs GeoJSON files for all 12 months

2. ✅ **Created test script** (`scripts/test_province_aggregation.py`)
   - Quick single-month test for verification
   - Validates aggregation approach

3. ✅ **Ran aggregation for all 12 months**
   - Successfully processed 4,596 provinces worldwide
   - Generated files: `data/provinces/aggregated/provinces_month_XX.geojson`
   - File size: ~56 MB per month (before optimization)

4. ✅ **Created province data loader** (`app/province_loader.py`)
   - Loads pre-computed province GeoJSON data
   - Caches data for performance
   - Supports all variable types (temperature, rainfall, sunshine, overall)

5. ✅ **Added API endpoints** (`app/routes.py`)
   - `/api/provinces` - Get province data for specific month/variable
   - `/api/provinces/available` - List available months

6. ✅ **Updated frontend** (`static/script.js`)
   - Created `createProvinceOverlay()` function
   - Displays province polygons with color-coded climate data
   - Interactive tooltips showing province name and climate values
   - Modified `updateMapLayers()` to use province data

7. ✅ **Created optimization script** (`scripts/optimize_province_geojson.py`)
   - Simplifies geometry for smaller file sizes
   - Removes unnecessary properties
   - Targets ~30-40% file size reduction

#### Data Structure:

**GeoJSON Properties per Province:**

- `name` - Province/state name
- `admin` - Country name
- `iso_a2` - Country ISO code
- `tmin_mean` - Average minimum temperature (°C)
- `tmax_mean` - Average maximum temperature (°C)
- `temp_avg` - Average temperature (°C)
- `prec_mean` - Average precipitation (mm/day)
- `sunhours_mean` - Average sunshine hours (hours/day)
- `overall_score` - Composite weather score (0-1)

#### Next Steps:

- [ ] Complete optimization of all 12 month files
- [ ] Update province_loader.py to use optimized directory
- [ ] Test frontend visualization thoroughly
- [ ] Add loading indicators for large files
- [ ] Consider further optimizations (topojson, server-side filtering)
- [ ] Document new API endpoints in README

#### Notes:

- Original grid-based data is preserved (not deleted)
- Province data provides faster, cleaner visualization
- File sizes: ~56 MB unoptimized, ~35 MB optimized (estimated)
- Supports 4,596 provinces/states globally
