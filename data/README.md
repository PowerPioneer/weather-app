# Climate Data Directory Structure

This directory contains climate data from multiple sources used by the "Where to Go for Great Weather" application.

## Data Sources

### 1. ERA5 (`era5/`)
**Source:** ERA5 Reanalysis from ECMWF (European Centre for Medium-Range Weather Forecasts)
**Website:** https://www.ecmwf.int/en/forecasts/dataset/ecmwf-reanalysis-v5
**License:** Free for non-commercial and commercial use
**Resolution:** 0.25° × 0.25° (approximately 25 km)

**Variables:**
- `tmin/` - Monthly minimum temperature (°C)
- `tmax/` - Monthly maximum temperature (°C)  
- `prec/` - Monthly precipitation (mm)

**Format:** GeoTIFF files per year-month
**Coverage:** 2020-2024 (5 years of monthly data)

### 2. CRU (`cru/`)
**Source:** CRU (Climatic Research Unit) Time-Series v4.09
**Website:** https://crudata.uea.ac.uk/cru/data/hrg/
**License:** Free for non-commercial use
**Resolution:** 10 arc-minutes

**Variables:**
- `sunhours/` - Monthly sunshine hours per day (hours/day)

**Format:** GeoTIFF files per month (e.g., `sunhours_01.tif`)
**Processing:** Converted from CRU sunshine percentage to hours/day using astronomical calculations

### 3. Provinces (`provinces/`)
**Source:** Natural Earth Admin-1 (States and Provinces)
**Website:** https://www.naturalearthdata.com/
**License:** Public Domain
**Resolution:** 1:10 million scale

**Files:**
- `ne_10m_admin_1_states_provinces.shp` - Shapefile with province boundaries
- `provinces.geojson` - Web-ready GeoJSON format (simplified geometries)
- `metadata.json` - Province dataset metadata

**Purpose:** For future province-level data aggregation

## Data Processing Scripts

All data processing scripts are located in the `scripts/` directory:

- `process_era5_data.py` - Process ERA5 temperature and precipitation data
- `process_cru_sunshine.py` - Convert CRU sunshine percentage to hours/day
- `download_province_boundaries.py` - Download and prepare province boundaries
- `download_country_boundaries.py` - Download and prepare country boundaries
- `download_era5_data.py` - Download ERA5 data from ECMWF

## Citation

If you use this data in your work, please cite the original sources:

**ERA5:**
> Hersbach, H., Bell, B., Berrisford, P., et al. (2020): The ERA5 global reanalysis. Quarterly Journal of the Royal Meteorological Society, 146(730), 1999-2049.

**CRU:**
> Harris, I., Osborn, T.J., Jones, P. et al. Version 4 of the CRU TS monthly high-resolution gridded multivariate climate dataset. Sci Data 7, 109 (2020).

**Natural Earth:**
> Natural Earth. Free vector and raster map data @ naturalearthdata.com.
