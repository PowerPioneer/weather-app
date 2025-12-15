"""
Optimize GeoJSON files by simplifying geometry and removing unnecessary data.
This reduces file sizes for faster web loading.
"""
import geopandas as gpd
from pathlib import Path
import json

BASE_DIR = Path(__file__).parent.parent
AGGREGATED_DIR = BASE_DIR / "data" / "provinces" / "aggregated"
OPTIMIZED_DIR = BASE_DIR / "data" / "provinces" / "optimized"

def optimize_month(month):
    """Optimize a single month's GeoJSON file."""
    input_file = AGGREGATED_DIR / f"provinces_month_{month:02d}.geojson"
    output_file = OPTIMIZED_DIR / f"provinces_month_{month:02d}.geojson"
    
    print(f"Optimizing month {month}...")
    print(f"  Input: {input_file}")
    
    # Load GeoDataFrame
    gdf = gpd.read_file(input_file)
    
    # Simplify geometry (tolerance in degrees, ~0.01 = ~1km)
    print(f"  Simplifying geometry...")
    gdf['geometry'] = gdf['geometry'].simplify(tolerance=0.01, preserve_topology=True)
    
    # Keep only essential columns
    essential_cols = [
        'name', 'admin', 'iso_a2',
        'tmin_mean', 'tmax_mean', 'temp_avg',
        'prec_mean', 'sunhours_mean', 'overall_score',
        'geometry'
    ]
    gdf = gdf[[col for col in essential_cols if col in gdf.columns]]
    
    # Save optimized version
    print(f"  Saving to {output_file}...")
    gdf.to_file(output_file, driver='GeoJSON')
    
    # Compare sizes
    input_size = input_file.stat().st_size / (1024 * 1024)
    output_size = output_file.stat().st_size / (1024 * 1024)
    reduction = (1 - output_size/input_size) * 100
    
    print(f"  Original: {input_size:.2f} MB")
    print(f"  Optimized: {output_size:.2f} MB")
    print(f"  Reduction: {reduction:.1f}%")
    
    return output_size

def main():
    print("="*60)
    print("Optimizing Province GeoJSON Files")
    print("="*60)
    
    OPTIMIZED_DIR.mkdir(parents=True, exist_ok=True)
    
    total_size = 0
    
    for month in range(1, 13):
        try:
            size = optimize_month(month)
            total_size += size
            print()
        except Exception as e:
            print(f"Error optimizing month {month}: {e}")
            print()
    
    print("="*60)
    print(f"Total optimized size: {total_size:.2f} MB")
    print(f"Average per month: {total_size/12:.2f} MB")
    print("="*60)

if __name__ == '__main__':
    main()
