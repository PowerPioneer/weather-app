"""
Process CRU CL v2.0 sunshine data to GeoTIFF format.

This script:
1. Reads the CRU grid_10min_sunp.dat.gz file (sunshine as % of max possible)
2. Converts sunshine percentage to hours per day using astronomical calculations
3. Saves as GeoTIFF files for each month (compatible with WorldClim structure)
"""

import gzip
import numpy as np
from pathlib import Path
import rasterio
from rasterio.transform import from_origin
import math

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
CRU_FILE = DATA_DIR / "grid_10min_sunp.dat.gz"
OUTPUT_DIR = DATA_DIR / "cru" / "sunhours"

# CRU CL v2.0 specifications
CRU_RESOLUTION = 1/6  # 10 arc-minutes = 1/6 degree
CRU_NLAT = 1080  # Number of latitude cells (180° / 10')
CRU_NLON = 2160  # Number of longitude cells (360° / 10')

def calculate_day_length(latitude, month):
    """
    Calculate day length (hours) for a given latitude and month.
    
    Args:
        latitude: Latitude in degrees (-90 to 90)
        month: Month number (1-12)
    
    Returns:
        Day length in hours
    """
    # Use middle day of month
    day_of_year = [15, 45, 74, 105, 135, 162, 198, 228, 258, 288, 318, 344][month - 1]
    
    # Solar declination (simplified)
    declination = 23.45 * math.sin(math.radians((360 / 365.25) * (day_of_year - 81)))
    
    # Convert latitude to radians
    lat_rad = math.radians(latitude)
    dec_rad = math.radians(declination)
    
    # Hour angle at sunrise/sunset
    try:
        cos_hour_angle = -math.tan(lat_rad) * math.tan(dec_rad)
        
        # Handle polar day/night
        if cos_hour_angle > 1:
            return 0  # Polar night
        elif cos_hour_angle < -1:
            return 24  # Polar day
        
        hour_angle = math.acos(cos_hour_angle)
        day_length = (2 * math.degrees(hour_angle)) / 15  # Convert to hours
        
        return day_length
    except:
        return 12  # Fallback to 12 hours


def read_cru_sunshine():
    """
    Read CRU sunshine data from gzipped text file.
    
    Returns:
        Dictionary with monthly sunshine data (% of maximum)
    """
    print(f"Reading CRU sunshine data from {CRU_FILE}")
    
    # Initialize monthly arrays
    monthly_data = {month: np.full((CRU_NLAT, CRU_NLON), np.nan, dtype=np.float32) 
                   for month in range(1, 13)}
    
    with gzip.open(CRU_FILE, 'rt') as f:
        for line_num, line in enumerate(f, 1):
            if line_num % 100000 == 0:
                print(f"  Processed {line_num} lines...")
            
            parts = line.strip().split()
            if len(parts) < 14:  # lat, lon, 12 months
                continue
            
            try:
                lat = float(parts[0])
                lon = float(parts[1])
                monthly_values = [float(x) if x != '-999' else np.nan for x in parts[2:14]]
                
                # Convert lat/lon to grid indices
                # CRU grid: lat from 89.9167 to -89.9167, lon from -179.9167 to 179.9167
                lat_idx = int((90 - lat) / CRU_RESOLUTION)
                lon_idx = int((lon + 180) / CRU_RESOLUTION)
                
                # Check bounds
                if 0 <= lat_idx < CRU_NLAT and 0 <= lon_idx < CRU_NLON:
                    for month in range(1, 13):
                        monthly_data[month][lat_idx, lon_idx] = monthly_values[month - 1]
                        
            except (ValueError, IndexError) as e:
                print(f"  Warning: Error parsing line {line_num}: {e}")
                continue
    
    print(f"✓ Loaded sunshine data for {line_num} locations")
    return monthly_data


def convert_to_sunshine_hours(sunp_data, month):
    """
    Convert sunshine percentage to hours per day.
    
    Args:
        sunp_data: 2D array of sunshine percentage (0-100)
        month: Month number (1-12)
    
    Returns:
        2D array of sunshine hours per day
    """
    print(f"  Converting sunshine % to hours for month {month}")
    
    sunhours = np.full_like(sunp_data, np.nan)
    
    # Calculate for each latitude
    for lat_idx in range(CRU_NLAT):
        # Calculate latitude for this row
        latitude = 90 - (lat_idx * CRU_RESOLUTION)
        
        # Calculate day length for this latitude and month
        day_length = calculate_day_length(latitude, month)
        
        # Convert percentage to hours
        sunhours[lat_idx, :] = (sunp_data[lat_idx, :] / 100.0) * day_length
    
    return sunhours


def save_as_geotiff(data, month, output_dir):
    """
    Save sunshine hours data as GeoTIFF.
    
    Args:
        data: 2D numpy array of sunshine hours
        month: Month number (1-12)
        output_dir: Output directory path
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"sunhours_{month:02d}.tif"
    
    # Create transform (CRU grid starts at top-left: -180, 90)
    transform = from_origin(-180, 90, CRU_RESOLUTION, CRU_RESOLUTION)
    
    # Write GeoTIFF
    with rasterio.open(
        output_file,
        'w',
        driver='GTiff',
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype=data.dtype,
        crs='EPSG:4326',
        transform=transform,
        compress='lzw',
        nodata=np.nan
    ) as dst:
        dst.write(data, 1)
    
    print(f"  ✓ Saved {output_file}")


def main():
    """Main processing function."""
    print("=" * 60)
    print("CRU CL v2.0 Sunshine Data Processing")
    print("=" * 60)
    
    # Check if input file exists
    if not CRU_FILE.exists():
        print(f"ERROR: CRU data file not found at {CRU_FILE}")
        print("Please download it from:")
        print("https://crudata.uea.ac.uk/cru/data/hrg/tmc/grid_10min_sunp.dat.gz")
        return
    
    # Read CRU sunshine percentage data
    print("\n1. Reading CRU sunshine data...")
    sunp_monthly = read_cru_sunshine()
    
    # Convert to sunshine hours and save
    print("\n2. Converting to sunshine hours and saving...")
    for month in range(1, 13):
        print(f"\nMonth {month}:")
        sunhours = convert_to_sunshine_hours(sunp_monthly[month], month)
        save_as_geotiff(sunhours, month, OUTPUT_DIR)
    
    print("\n" + "=" * 60)
    print("✓ Processing complete!")
    print(f"Output files saved to: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
