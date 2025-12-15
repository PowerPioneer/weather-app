"""
Process ERA5 NetCDF data and convert to GeoTIFF format.

This script converts raw ERA5 NetCDF files to monthly GeoTIFF files compatible
with the existing data loader infrastructure. It processes:
- 2m temperature → tmin and tmax GeoTIFFs (deriving statistics)
- Total precipitation → prec GeoTIFFs (converting meters to mm)

Usage:
    python scripts/process_era5_data.py
"""

import xarray as xr
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from pathlib import Path
import json
from datetime import datetime

def create_metadata():
    """Create metadata file for ERA5 data."""
    metadata = {
        "source": "ERA5",
        "description": "ERA5 is the fifth generation ECMWF reanalysis for global climate and weather",
        "resolution": "0.25 degrees (~28 km)",
        "period": "2020-2024 (5 years monthly averages)",
        "variables": {
            "tmin": "Minimum 2m temperature (°C)",
            "tmax": "Maximum 2m temperature (°C)",
            "prec": "Daily average precipitation (mm/day)"
        },
        "license": "CC-BY 4.0 (free for commercial use)",
        "citation": "Hersbach et al. (2020): ERA5 monthly averaged data on single levels. Copernicus Climate Change Service (C3S) Climate Data Store (CDS). DOI: 10.24381/cds.f17050d7",
        "website": "https://cds.climate.copernicus.eu/",
        "notes": [
            "Temperature statistics derived from monthly mean 2m temperature",
            "Precipitation: ERA5 monthly means provide daily averages (mm/day)",
            "Precipitation converted from meters to millimeters",
            "Data accessed via Copernicus Climate Data Store",
            "Commercial use permitted under CC-BY 4.0 license"
        ],
        "processed_date": datetime.now().isoformat()
    }
    return metadata

def kelvin_to_celsius(temp_k):
    """Convert temperature from Kelvin to Celsius."""
    return temp_k - 273.15

def meters_to_mm(meters):
    """
    Convert precipitation from meters to millimeters.
    ERA5 monthly means already provide daily average precipitation.
    """
    return meters * 1000.0

def save_as_geotiff(data_array, output_path, nodata=-9999):
    """
    Save an xarray DataArray as a GeoTIFF file.
    
    Args:
        data_array: xarray DataArray with latitude/longitude coordinates
        output_path: Path to output GeoTIFF file
        nodata: NoData value to use
    """
    # Get dimensions
    lats = data_array.latitude.values
    lons = data_array.longitude.values
    
    # ERA5 uses longitude from 0-360, we need to convert to -180 to 180
    # Roll the array so that longitude 0-180 becomes -180 to 0, and 180-360 becomes 0 to 180
    if lons[0] >= 0 and lons[-1] > 180:
        # Find the split point (where lon crosses 180)
        split_idx = np.searchsorted(lons, 180.0)
        
        # Roll the data array
        data_array = data_array.roll(longitude=len(lons) - split_idx, roll_coords=True)
        
        # Adjust longitude values to -180 to 180 range
        lons = data_array.longitude.values
        lons = np.where(lons > 180, lons - 360, lons)
        
        # Sort the longitude indices to ensure they're in ascending order
        lon_sort_idx = np.argsort(lons)
        data_array = data_array.isel(longitude=lon_sort_idx)
        data_array = data_array.assign_coords(longitude=np.sort(lons))
        
        # Re-get the adjusted values
        lons = data_array.longitude.values
    
    # ERA5 uses latitude from North to South (90 to -90)
    # We need to flip if necessary to go from North to South
    if lats[0] < lats[-1]:
        data_array = data_array.isel(latitude=slice(None, None, -1))
        lats = data_array.latitude.values
    
    # Get the data
    data = data_array.values
    
    # Replace NaN with nodata value
    data = np.where(np.isnan(data), nodata, data)
    
    # Calculate transform
    # ERA5 is on a regular lat-lon grid
    lat_res = abs(lats[1] - lats[0])
    lon_res = abs(lons[1] - lons[0])
    
    transform = from_bounds(
        west=lons.min() - lon_res/2,
        south=lats.min() - lat_res/2,
        east=lons.max() + lon_res/2,
        north=lats.max() + lat_res/2,
        width=len(lons),
        height=len(lats)
    )
    
    # Write GeoTIFF
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with rasterio.open(
        output_path,
        'w',
        driver='GTiff',
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype=data.dtype,
        crs='EPSG:4326',
        transform=transform,
        nodata=nodata,
        compress='lzw'
    ) as dst:
        dst.write(data, 1)

def process_temperature(input_file, output_dir):
    """
    Process temperature data from ERA5.
    
    For each month, we derive tmin and tmax from the monthly mean temperature.
    Since ERA5 monthly means don't include daily extremes, we estimate:
    - tmin ≈ monthly_mean - 5°C (conservative estimate)
    - tmax ≈ monthly_mean + 5°C (conservative estimate)
    
    Note: For more accurate min/max, daily ERA5 data would be needed.
    """
    print("\n-> Processing temperature data...")
    
    ds = xr.open_dataset(input_file)
    temp_var = ds['t2m']  # 2m temperature in Kelvin
    
    # Get unique year-month combinations
    times = temp_var.valid_time.values
    
    for time_idx, time in enumerate(times):
        # Extract month and year
        time_obj = np.datetime64(time, 'M').astype(datetime)
        year = time_obj.year
        month = time_obj.month
        
        print(f"  Processing {year}-{month:02d}...")
        
        # Get temperature for this time
        temp_k = temp_var.isel(valid_time=time_idx)
        temp_c = kelvin_to_celsius(temp_k)
        
        # Estimate min and max (rough approximation)
        # For better accuracy, would need daily data
        temp_min = temp_c - 5.0
        temp_max = temp_c + 5.0
        
        # Save tmin
        tmin_path = output_dir / 'tmin' / f'era5_tmin_{year}-{month:02d}.tif'
        save_as_geotiff(temp_min, tmin_path)
        
        # Save tmax
        tmax_path = output_dir / 'tmax' / f'era5_tmax_{year}-{month:02d}.tif'
        save_as_geotiff(temp_max, tmax_path)
    
    ds.close()
    print("  [OK] Temperature processing complete")

def process_precipitation(input_file, output_dir):
    """
    Process precipitation data from ERA5.
    
    Converts precipitation from meters to millimeters.
    ERA5 monthly means provide daily average precipitation.
    """
    print("\n-> Processing precipitation data...")
    
    ds = xr.open_dataset(input_file)
    prec_var = ds['tp']  # Daily average precipitation in meters
    
    # Get unique year-month combinations
    times = prec_var.valid_time.values
    
    for time_idx, time in enumerate(times):
        # Extract month and year
        time_obj = np.datetime64(time, 'M').astype(datetime)
        year = time_obj.year
        month = time_obj.month
        
        print(f"  Processing {year}-{month:02d}...")
        
        # Get precipitation for this time (daily average in meters)
        prec_m_per_day = prec_var.isel(valid_time=time_idx)
        # Convert to daily average in mm
        prec_mm_per_day = meters_to_mm(prec_m_per_day)
        
        # Save precipitation
        prec_path = output_dir / 'prec' / f'era5_prec_{year}-{month:02d}.tif'
        save_as_geotiff(prec_mm_per_day, prec_path)
    
    ds.close()
    print("  [OK] Precipitation processing complete")

def calculate_statistics(output_dir):
    """Calculate statistics for all processed data."""
    print("\n-> Calculating statistics...")
    
    stats = {
        "variables": {},
        "period": "2020-2024",
        "resolution": "0.25 degrees"
    }
    
    variables = ['tmin', 'tmax', 'prec']
    
    for var in variables:
        var_dir = output_dir / var
        if not var_dir.exists():
            continue
        
        var_stats = {}
        tif_files = sorted(var_dir.glob('*.tif'))
        
        print(f"  Processing {var}: {len(tif_files)} files")
        
        for tif_file in tif_files:
            with rasterio.open(tif_file) as src:
                data = src.read(1)
                # Mask nodata values
                valid_data = data[data != src.nodata]
                
                if len(valid_data) > 0:
                    month = tif_file.stem.split('_')[-1]  # Extract YYYY-MM
                    var_stats[month] = {
                        "min": float(np.min(valid_data)),
                        "max": float(np.max(valid_data)),
                        "mean": float(np.mean(valid_data)),
                        "std": float(np.std(valid_data))
                    }
        
        stats["variables"][var] = var_stats
    
    # Save statistics
    stats_file = output_dir.parent.parent / 'app' / 'static' / 'data' / 'era5_stats.json'
    stats_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    
    print(f"  [OK] Statistics saved to {stats_file}")

def main():
    """Main processing function."""
    print("=" * 80)
    print("ERA5 Data Processing")
    print("=" * 80)
    
    # Setup paths
    base_dir = Path(__file__).parent.parent
    raw_dir = base_dir / 'data' / 'era5' / 'raw'
    output_dir = base_dir / 'data' / 'era5'
    
    temp_file = raw_dir / 'era5_temperature_monthly_2020-2024.nc'
    prec_file = raw_dir / 'era5_precipitation_monthly_2020-2024.nc'
    
    # Check if input files exist
    if not temp_file.exists():
        print(f"[ERROR] Temperature file not found: {temp_file}")
        print("  Run download_era5_data.py first")
        return False
    
    if not prec_file.exists():
        print(f"[ERROR] Precipitation file not found: {prec_file}")
        print("  Run download_era5_data.py first")
        return False
    
    print(f"Input directory: {raw_dir}")
    print(f"Output directory: {output_dir}")
    print("=" * 80)
    
    # Process temperature
    process_temperature(temp_file, output_dir)
    
    # Process precipitation
    process_precipitation(prec_file, output_dir)
    
    # Calculate statistics
    calculate_statistics(output_dir)
    
    # Create metadata
    metadata = create_metadata()
    metadata_file = output_dir / 'metadata.json'
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"\n[OK] Metadata saved to {metadata_file}")
    
    print("\n" + "=" * 80)
    print("[OK] Processing complete!")
    print("=" * 80)
    print(f"\nGenerated files:")
    print(f"  - Temperature (min/max): {output_dir / 'tmin'} and {output_dir / 'tmax'}")
    print(f"  - Precipitation: {output_dir / 'prec'}")
    print(f"  - Statistics: {base_dir / 'app' / 'static' / 'data' / 'era5_stats.json'}")
    print(f"  - Metadata: {metadata_file}")
    
    return True

if __name__ == '__main__':
    success = main()
    if not success:
        exit(1)
