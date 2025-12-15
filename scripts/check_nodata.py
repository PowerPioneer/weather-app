"""Check nodata values in raster files."""
import rasterio
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
ERA5_DIR = BASE_DIR / "data" / "era5"

# Check tmin file
tif_file = ERA5_DIR / "tmin" / "era5_tmin_2020-01.tif"

with rasterio.open(tif_file) as src:
    print(f"File: {tif_file.name}")
    print(f"NoData value: {src.nodata}")
    print(f"Data type: {src.dtypes[0]}")
    
    data = src.read(1)
    print(f"Shape: {data.shape}")
    print(f"Min value: {data.min()}")
    print(f"Max value: {data.max()}")
    
    # Check for special values
    print(f"\nValue statistics:")
    print(f"  Count of -9999: {(data == -9999).sum()}")
    print(f"  Count of NaN: {np.isnan(data).sum()}")
    print(f"  Count of valid values: {((data != -9999) & ~np.isnan(data)).sum()}")
    
    # Sample of unique values
    valid_data = data[(data != -9999) & ~np.isnan(data)]
    if len(valid_data) > 0:
        print(f"\nValid data range: {valid_data.min():.2f} to {valid_data.max():.2f}")
        print(f"Valid data mean: {valid_data.mean():.2f}")
