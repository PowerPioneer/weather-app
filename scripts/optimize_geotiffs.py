"""
Optimize GeoTIFF files for server deployment by:
1. Computing monthly averages across all years (2020-2024)
2. Compressing with deflate compression
3. Reducing from 186 files to 48 files (12 months × 4 variables)

This reduces storage by ~75% while maintaining data quality.
"""
import rasterio
from rasterio.enums import Resampling
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
ERA5_DIR = BASE_DIR / "data" / "era5"
CRU_DIR = BASE_DIR / "data" / "cru"
OUTPUT_DIR = BASE_DIR / "data" / "optimized"

def average_monthly_geotiffs(variable, month, output_dir):
    """
    Average all yearly GeoTIFFs for a given month into a single optimized file.
    
    Args:
        variable: 'tmin', 'tmax', 'prec', or 'sunhours'
        month: Month number (1-12)
        output_dir: Directory to save optimized GeoTIFF
    """
    # Determine source directory
    if variable == 'sunhours':
        var_dir = CRU_DIR / variable
        # Sunhours already has one file per month
        source_pattern = f"*_{month:02d}.tif"
    else:
        var_dir = ERA5_DIR / variable
        source_pattern = f"*-{month:02d}.tif"
    
    if not var_dir.exists():
        print(f"Warning: Directory not found: {var_dir}")
        return False
    
    # Find all files for this month
    tif_files = sorted(list(var_dir.glob(source_pattern)))
    
    if not tif_files:
        print(f"Warning: No files found for {variable} month {month}")
        return False
    
    print(f"Processing {variable} month {month:02d}: {len(tif_files)} file(s)")
    
    # Read all files and compute average
    all_data = []
    profile = None
    
    for tif_file in tif_files:
        with rasterio.open(tif_file) as src:
            if profile is None:
                profile = src.profile.copy()
            
            data = src.read(1)
            nodata = src.nodata if src.nodata is not None else -9999
            
            # Mask nodata values
            masked_data = np.ma.masked_equal(data, nodata)
            all_data.append(masked_data)
    
    # Compute mean across all years
    stacked = np.ma.stack(all_data)
    averaged = np.ma.mean(stacked, axis=0)
    
    # Fill masked values with nodata
    result = averaged.filled(-9999)
    
    # Update profile for compression
    profile.update(
        dtype=rasterio.float32,
        compress='deflate',
        predictor=3,  # Floating point predictor
        zlevel=9,  # Maximum compression
        nodata=-9999,
        tiled=True,
        blockxsize=256,
        blockysize=256
    )
    
    # Output filename
    output_file = output_dir / variable / f"{variable}_month_{month:02d}.tif"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Write optimized file
    with rasterio.open(output_file, 'w', **profile) as dst:
        dst.write(result.astype(rasterio.float32), 1)
    
    # Compare sizes
    input_size = sum(f.stat().st_size for f in tif_files) / (1024 * 1024)
    output_size = output_file.stat().st_size / (1024 * 1024)
    reduction = (1 - output_size / input_size) * 100
    
    print(f"  Input: {input_size:.2f} MB ({len(tif_files)} files)")
    print(f"  Output: {output_size:.2f} MB (1 file)")
    print(f"  Reduction: {reduction:.1f}%")
    
    return True

def main():
    print("="*70)
    print("OPTIMIZING GEOTIFF FILES FOR SERVER DEPLOYMENT")
    print("="*70)
    print()
    
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    variables = ['tmin', 'tmax', 'prec', 'sunhours']
    months = range(1, 13)
    
    total_input_size = 0
    total_output_size = 0
    success_count = 0
    
    for variable in variables:
        print(f"\n{variable.upper()}")
        print("-" * 70)
        
        for month in months:
            if average_monthly_geotiffs(variable, month, OUTPUT_DIR):
                success_count += 1
            print()
    
    # Calculate total sizes
    for variable in variables:
        if variable == 'sunhours':
            var_dir = CRU_DIR / variable
        else:
            var_dir = ERA5_DIR / variable
        
        if var_dir.exists():
            files = list(var_dir.glob("*.tif"))
            total_input_size += sum(f.stat().st_size for f in files)
    
    optimized_files = list(OUTPUT_DIR.rglob("*.tif"))
    total_output_size = sum(f.stat().st_size for f in optimized_files)
    
    total_input_mb = total_input_size / (1024 * 1024)
    total_output_mb = total_output_size / (1024 * 1024)
    total_reduction = (1 - total_output_size / total_input_size) * 100 if total_input_size > 0 else 0
    
    print("="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Files processed: {success_count}")
    print(f"Total input size: {total_input_mb:.2f} MB")
    print(f"Total output size: {total_output_mb:.2f} MB")
    print(f"Total reduction: {total_reduction:.1f}%")
    print(f"Space saved: {total_input_mb - total_output_mb:.2f} MB")
    print()
    print("✓ Optimization complete!")
    print(f"  Optimized files saved to: {OUTPUT_DIR}")

if __name__ == '__main__':
    main()
