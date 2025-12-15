# Where to go for great weather - Bug Fixes

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

