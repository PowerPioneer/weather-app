"""
Aggregate climate data per province/state for all months.
This script processes ERA5 and CRU data to compute province-level averages.

Output: GeoJSON files with province polygons and average climate values for each month.
"""
import geopandas as gpd
import rasterio
from rasterstats import zonal_stats
from pathlib import Path
import json
import numpy as np
from datetime import datetime

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
ERA5_DIR = DATA_DIR / "era5"
CRU_DIR = DATA_DIR / "cru"
PROVINCES_DIR = DATA_DIR / "provinces"
OUTPUT_DIR = DATA_DIR / "provinces" / "aggregated"

# Load province boundaries
PROVINCES_SHAPEFILE = PROVINCES_DIR / "ne_10m_admin_1_states_provinces.shp"

def load_provinces():
    """Load province boundaries from shapefile."""
    print(f"Loading provinces from {PROVINCES_SHAPEFILE}...")
    gdf = gpd.read_file(PROVINCES_SHAPEFILE)
    print(f"Loaded {len(gdf)} provinces/states")
    
    # Keep only essential columns to reduce file size
    columns_to_keep = [
        'name', 'name_alt', 'admin', 'iso_a2', 'iso_3166_2',
        'type', 'latitude', 'longitude', 'geometry'
    ]
    gdf = gdf[[col for col in columns_to_keep if col in gdf.columns]]
    
    # Ensure CRS is WGS84 (EPSG:4326) to match climate data
    if gdf.crs != 'EPSG:4326':
        print(f"Converting CRS from {gdf.crs} to EPSG:4326...")
        gdf = gdf.to_crs('EPSG:4326')
    
    return gdf

def aggregate_variable_for_month(variable, month, provinces_gdf):
    """
    Aggregate a single variable for a single month across all provinces.
    
    Args:
        variable: 'tmin', 'tmax', 'prec', or 'sunhours'
        month: Month number (1-12)
        provinces_gdf: GeoDataFrame with province boundaries
    
    Returns:
        GeoDataFrame with aggregated statistics per province
    """
    # Determine source directory
    if variable == 'sunhours':
        var_dir = CRU_DIR / variable
    else:
        var_dir = ERA5_DIR / variable
    
    if not var_dir.exists():
        print(f"Warning: Directory not found: {var_dir}")
        return None
    
    # Find all GeoTIFF files for this month (across all years)
    tif_files = list(var_dir.glob(f"*-{month:02d}.tif"))
    if not tif_files:
        tif_files = list(var_dir.glob(f"*_{month:02d}.tif"))
    
    if not tif_files:
        print(f"Warning: No files found for {variable} month {month}")
        return None
    
    tif_files = sorted(tif_files)
    print(f"  Found {len(tif_files)} file(s) for {variable} month {month}")
    
    # Aggregate statistics from all years
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
                stats=['mean', 'min', 'max', 'count'],
                nodata=nodata_value,
                all_touched=True  # Include any pixel that touches the polygon (better for small provinces)
            )
            all_stats.append(stats)
        except Exception as e:
            print(f"    Error processing {tif_file}: {e}")
            continue
    
    if not all_stats:
        return None
    
    # Average across all years
    result_gdf = provinces_gdf.copy()
    
    # Compute mean of means across all years
    # Set reasonable thresholds per variable to filter nodata
    valid_range = {
        'tmin': (-90, 60),
        'tmax': (-90, 60),
        'prec': (0, 1000),
        'sunhours': (0, 24)
    }
    
    min_val, max_val = valid_range.get(variable, (-100, 1000))
    
    mean_values = []
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

def create_province_dataset_for_month(month, provinces_gdf):
    """
    Create a complete province dataset for one month with all variables.
    
    Args:
        month: Month number (1-12)
        provinces_gdf: Base GeoDataFrame with province boundaries
    
    Returns:
        GeoDataFrame with all climate variables aggregated
    """
    print(f"\nProcessing month {month}...")
    result = provinces_gdf.copy()
    
    # Process each variable
    variables = ['tmin', 'tmax', 'prec', 'sunhours']
    
    for variable in variables:
        print(f"  Aggregating {variable}...")
        var_data = aggregate_variable_for_month(variable, month, provinces_gdf)
        
        if var_data is not None:
            # Add the mean column to result
            result[f'{variable}_mean'] = var_data[f'{variable}_mean']
        else:
            result[f'{variable}_mean'] = None
    
    # Calculate derived metrics
    # Temperature: average of tmin and tmax
    result['temp_avg'] = result.apply(
        lambda row: (
            (row['tmin_mean'] + row['tmax_mean']) / 2.0
            if row['tmin_mean'] is not None and row['tmax_mean'] is not None
            else None
        ),
        axis=1
    )
    
    # Overall score: simple composite based on preferences
    # Higher is better weather (warm, low rain, high sun)
    # Normalize each component to 0-1 scale
    def calculate_score(row):
        try:
            # Target ranges (from typical user preferences)
            target_temp = 23  # °C
            target_rain = 0   # mm/day (less is better)
            target_sun = 10   # hours/day
            
            score = 0
            count = 0
            
            # Temperature component (20-30°C is ideal)
            if row['temp_avg'] is not None:
                temp_score = 1.0 - min(abs(row['temp_avg'] - target_temp) / 15.0, 1.0)
                score += temp_score
                count += 1
            
            # Rain component (less is better, up to 5mm/day acceptable)
            if row['prec_mean'] is not None:
                rain_score = max(0, 1.0 - row['prec_mean'] / 5.0)
                score += rain_score
                count += 1
            
            # Sun component (more is better, up to 12 hours)
            if row['sunhours_mean'] is not None:
                sun_score = min(row['sunhours_mean'] / 12.0, 1.0)
                score += sun_score
                count += 1
            
            return score / count if count > 0 else None
        except:
            return None
    
    result['overall_score'] = result.apply(calculate_score, axis=1)
    
    return result

def save_province_data(gdf, month, output_dir):
    """
    Save province data to GeoJSON file.
    
    Args:
        gdf: GeoDataFrame with province data
        month: Month number (1-12)
        output_dir: Output directory path
    """
    output_file = output_dir / f"provinces_month_{month:02d}.geojson"
    
    # Convert to GeoJSON (automatically handles geometry)
    print(f"  Saving to {output_file}...")
    gdf.to_file(output_file, driver='GeoJSON')
    
    # Calculate file size
    size_mb = output_file.stat().st_size / (1024 * 1024)
    print(f"  File size: {size_mb:.2f} MB")
    
    # Generate statistics
    stats = {
        'month': month,
        'province_count': len(gdf),
        'file_size_mb': round(size_mb, 2),
        'variables': {
            'tmin': {
                'min': float(gdf['tmin_mean'].min()) if gdf['tmin_mean'].notna().any() else None,
                'max': float(gdf['tmin_mean'].max()) if gdf['tmin_mean'].notna().any() else None,
                'mean': float(gdf['tmin_mean'].mean()) if gdf['tmin_mean'].notna().any() else None
            },
            'tmax': {
                'min': float(gdf['tmax_mean'].min()) if gdf['tmax_mean'].notna().any() else None,
                'max': float(gdf['tmax_mean'].max()) if gdf['tmax_mean'].notna().any() else None,
                'mean': float(gdf['tmax_mean'].mean()) if gdf['tmax_mean'].notna().any() else None
            },
            'prec': {
                'min': float(gdf['prec_mean'].min()) if gdf['prec_mean'].notna().any() else None,
                'max': float(gdf['prec_mean'].max()) if gdf['prec_mean'].notna().any() else None,
                'mean': float(gdf['prec_mean'].mean()) if gdf['prec_mean'].notna().any() else None
            },
            'sunhours': {
                'min': float(gdf['sunhours_mean'].min()) if gdf['sunhours_mean'].notna().any() else None,
                'max': float(gdf['sunhours_mean'].max()) if gdf['sunhours_mean'].notna().any() else None,
                'mean': float(gdf['sunhours_mean'].mean()) if gdf['sunhours_mean'].notna().any() else None
            }
        }
    }
    
    return stats

def main():
    """Main execution function."""
    print("="*60)
    print("Province-Level Climate Data Aggregation")
    print("="*60)
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR}")
    
    # Load province boundaries
    provinces = load_provinces()
    
    # Process all 12 months
    all_month_stats = []
    
    for month in range(1, 13):
        try:
            # Create dataset for this month
            month_data = create_province_dataset_for_month(month, provinces)
            
            # Save to file
            stats = save_province_data(month_data, month, OUTPUT_DIR)
            all_month_stats.append(stats)
            
        except Exception as e:
            print(f"Error processing month {month}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Save overall metadata
    metadata = {
        'generated': datetime.now().isoformat(),
        'description': 'Province-level aggregated climate data',
        'source_data': {
            'ERA5': 'Temperature (tmin, tmax) and Precipitation',
            'CRU': 'Sunshine hours'
        },
        'total_provinces': len(provinces),
        'months_processed': len(all_month_stats),
        'variables': {
            'tmin_mean': 'Average minimum temperature (°C)',
            'tmax_mean': 'Average maximum temperature (°C)',
            'temp_avg': 'Average temperature (°C)',
            'prec_mean': 'Average precipitation (mm/day)',
            'sunhours_mean': 'Average sunshine hours (hours/day)',
            'overall_score': 'Composite weather score (0-1, higher is better)'
        },
        'month_stats': all_month_stats
    }
    
    metadata_file = OUTPUT_DIR / "metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\n{'='*60}")
    print("Processing Complete!")
    print(f"{'='*60}")
    print(f"Output files: {OUTPUT_DIR}")
    print(f"Metadata: {metadata_file}")
    print(f"Total provinces: {len(provinces)}")
    print(f"Months processed: {len(all_month_stats)}")
    
    # Print summary statistics
    total_size = sum(s['file_size_mb'] for s in all_month_stats)
    print(f"Total data size: {total_size:.2f} MB")
    print(f"Average file size: {total_size/len(all_month_stats):.2f} MB per month")

if __name__ == '__main__':
    main()
