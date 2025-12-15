"""
Apply land mask to ERA5 data to remove ocean values.

This script downloads Natural Earth land polygons and uses them to mask
ERA5 climate data, setting ocean pixels to NoData.
"""

import rasterio
from rasterio.mask import mask
from rasterio.features import geometry_mask
import numpy as np
from pathlib import Path
import geopandas as gpd
import requests
import zipfile
import io

def download_land_shapefile():
    """Download Natural Earth land polygons (1:110m scale for performance)."""
    data_dir = Path(__file__).parent.parent / 'data'
    land_dir = data_dir / 'land'
    land_dir.mkdir(exist_ok=True)
    
    shapefile_path = land_dir / 'ne_110m_land.shp'
    
    if shapefile_path.exists():
        print(f"Land shapefile already exists: {shapefile_path}")
        return shapefile_path
    
    print("Downloading Natural Earth land polygons...")
    url = "https://naciscdn.org/naturalearth/110m/physical/ne_110m_land.zip"
    
    response = requests.get(url)
    response.raise_for_status()
    
    print("Extracting shapefile...")
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        z.extractall(land_dir)
    
    print(f"Shapefile downloaded to {land_dir}")
    return shapefile_path

def apply_land_mask_to_file(input_path, output_path, land_geometries):
    """Apply land mask to a single GeoTIFF file."""
    with rasterio.open(input_path) as src:
        # Read the data
        data = src.read(1)
        
        # Create mask where True = ocean (to be masked out)
        # geometry_mask returns True for pixels outside geometries
        ocean_mask = geometry_mask(
            land_geometries,
            out_shape=(src.height, src.width),
            transform=src.transform,
            invert=False  # True = outside land = ocean
        )
        
        # Set ocean pixels to NoData
        nodata_value = src.nodata if src.nodata is not None else -9999
        data[ocean_mask] = nodata_value
        
        # Write masked data
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        profile = src.profile.copy()
        profile.update({
            'nodata': nodata_value
        })
        
        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(data, 1)

def main():
    """Apply land mask to all ERA5 data files."""
    print("="*80)
    print("Apply Land Mask to ERA5 Data")
    print("="*80)
    
    # Download/load land shapefile
    shapefile_path = download_land_shapefile()
    
    print("\nLoading land polygons...")
    land_gdf = gpd.read_file(shapefile_path)
    land_geometries = land_gdf.geometry.values
    print(f"Loaded {len(land_geometries)} land polygons")
    
    # Process ERA5 data
    era5_dir = Path(__file__).parent.parent / 'data' / 'era5'
    
    variables = ['tmin', 'tmax', 'prec']
    
    for var in variables:
        var_dir = era5_dir / var
        if not var_dir.exists():
            print(f"\nSkipping {var} (directory not found)")
            continue
        
        print(f"\n-> Processing {var}...")
        tif_files = sorted(var_dir.glob('*.tif'))
        
        for i, tif_file in enumerate(tif_files, 1):
            print(f"  [{i}/{len(tif_files)}] {tif_file.name}", end='')
            
            # Apply mask (overwrite original file)
            temp_output = tif_file.with_suffix('.tif.tmp')
            apply_land_mask_to_file(tif_file, temp_output, land_geometries)
            
            # Replace original with masked version
            temp_output.replace(tif_file)
            print(" ✓")
    
    print("\n" + "="*80)
    print("[OK] Land mask applied to all ERA5 files!")
    print("="*80)

if __name__ == '__main__':
    main()
