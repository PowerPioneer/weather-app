"""
Quick test: Aggregate climate data for just one month to verify the approach works.
"""
import geopandas as gpd
import rasterio
from rasterstats import zonal_stats
from pathlib import Path
import json
import numpy as np
from datetime import datetime
import sys

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
ERA5_DIR = DATA_DIR / "era5"
CRU_DIR = DATA_DIR / "cru"
PROVINCES_DIR = DATA_DIR / "provinces"
OUTPUT_DIR = DATA_DIR / "provinces" / "aggregated"

PROVINCES_SHAPEFILE = PROVINCES_DIR / "ne_10m_admin_1_states_provinces.shp"

def load_provinces():
    """Load province boundaries from shapefile."""
    print(f"Loading provinces from {PROVINCES_SHAPEFILE}...")
    gdf = gpd.read_file(PROVINCES_SHAPEFILE)
    print(f"Loaded {len(gdf)} provinces/states")
    
    # Keep only essential columns
    columns_to_keep = [
        'name', 'name_alt', 'admin', 'iso_a2', 'iso_3166_2',
        'type', 'latitude', 'longitude', 'geometry'
    ]
    gdf = gdf[[col for col in columns_to_keep if col in gdf.columns]]
    
    # Ensure CRS is WGS84
    if gdf.crs != 'EPSG:4326':
        print(f"Converting CRS from {gdf.crs} to EPSG:4326...")
        gdf = gdf.to_crs('EPSG:4326')
    
    return gdf

def aggregate_variable(variable, month, provinces_gdf):
    """Aggregate a single variable for a single month."""
    if variable == 'sunhours':
        var_dir = CRU_DIR / variable
    else:
        var_dir = ERA5_DIR / variable
    
    if not var_dir.exists():
        print(f"Warning: Directory not found: {var_dir}")
        return None
    
    # Find GeoTIFF files for this month
    tif_files = list(var_dir.glob(f"*-{month:02d}.tif"))
    if not tif_files:
        tif_files = list(var_dir.glob(f"*_{month:02d}.tif"))
    
    if not tif_files:
        print(f"Warning: No files found for {variable} month {month}")
        return None
    
    tif_files = sorted(tif_files)
    print(f"  Found {len(tif_files)} file(s) for {variable}")
    
    # Aggregate from all years
    all_stats = []
    
    for tif_file in tif_files:
        print(f"    Processing {tif_file.name}...")
        try:
            # First, check the nodata value from the raster
            with rasterio.open(str(tif_file)) as src:
                nodata_value = src.nodata if src.nodata is not None else -9999
            
            # Compute zonal statistics with proper nodata handling
            stats = zonal_stats(
                provinces_gdf.geometry,
                str(tif_file),
                stats=['mean'],
                nodata=nodata_value,
                all_touched=True  # Include any pixel that touches the polygon (better for small provinces)
            )
            all_stats.append(stats)
        except Exception as e:
            print(f"    Error: {e}")
            continue
    
    if not all_stats:
        return None
    
    # Average across years
    result_gdf = provinces_gdf.copy()
    mean_values = []
    
    # Set reasonable thresholds per variable
    valid_range = {
        'tmin': (-90, 60),
        'tmax': (-90, 60),
        'prec': (0, 1000),
        'sunhours': (0, 24)
    }
    
    min_val, max_val = valid_range.get(variable, (-100, 1000))
    
    for i in range(len(provinces_gdf)):
        province_means = [
            stats[i]['mean'] for stats in all_stats 
            if stats[i]['mean'] is not None 
            and not np.isnan(stats[i]['mean'])
            and min_val <= stats[i]['mean'] <= max_val
        ]
        if province_means:
            mean_values.append(float(np.mean(province_means)))
        else:
            mean_values.append(None)
    
    result_gdf[f'{variable}_mean'] = mean_values
    return result_gdf

def main():
    test_month = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    
    print(f"Testing province aggregation for month {test_month}")
    print("="*60)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load provinces
    provinces = load_provinces()
    
    # Test with one month
    print(f"\nProcessing month {test_month}...")
    result = provinces.copy()
    
    for variable in ['tmin', 'tmax', 'prec', 'sunhours']:
        print(f"  Aggregating {variable}...")
        var_data = aggregate_variable(variable, test_month, provinces)
        if var_data is not None:
            result[f'{variable}_mean'] = var_data[f'{variable}_mean']
        else:
            result[f'{variable}_mean'] = None
    
    # Calculate derived metrics
    result['temp_avg'] = result.apply(
        lambda row: (
            (row['tmin_mean'] + row['tmax_mean']) / 2.0
            if row['tmin_mean'] is not None and row['tmax_mean'] is not None
            else None
        ),
        axis=1
    )
    
    # Calculate overall score
    def calculate_score(row):
        try:
            target_temp = 23
            target_rain = 0
            target_sun = 10
            
            score = 0
            count = 0
            
            if row['temp_avg'] is not None:
                temp_score = 1.0 - min(abs(row['temp_avg'] - target_temp) / 15.0, 1.0)
                score += temp_score
                count += 1
            
            if row['prec_mean'] is not None:
                rain_score = max(0, 1.0 - row['prec_mean'] / 5.0)
                score += rain_score
                count += 1
            
            if row['sunhours_mean'] is not None:
                sun_score = min(row['sunhours_mean'] / 12.0, 1.0)
                score += sun_score
                count += 1
            
            return score / count if count > 0 else None
        except:
            return None
    
    result['overall_score'] = result.apply(calculate_score, axis=1)
    
    # Save
    output_file = OUTPUT_DIR / f"provinces_month_{test_month:02d}.geojson"
    print(f"\nSaving to {output_file}...")
    result.to_file(output_file, driver='GeoJSON')
    
    size_mb = output_file.stat().st_size / (1024 * 1024)
    print(f"File size: {size_mb:.2f} MB")
    print(f"Provinces with data: {result['temp_avg'].notna().sum()}")
    
    # Print sample statistics
    print("\nSample statistics:")
    print(f"  Temperature (avg): {result['temp_avg'].mean():.1f}°C (range: {result['temp_avg'].min():.1f} to {result['temp_avg'].max():.1f})")
    print(f"  Precipitation: {result['prec_mean'].mean():.1f} mm/day (range: {result['prec_mean'].min():.1f} to {result['prec_mean'].max():.1f})")
    print(f"  Sunshine: {result['sunhours_mean'].mean():.1f} hours/day (range: {result['sunhours_mean'].min():.1f} to {result['sunhours_mean'].max():.1f})")
    
    print("\nTest complete!")

if __name__ == '__main__':
    main()
