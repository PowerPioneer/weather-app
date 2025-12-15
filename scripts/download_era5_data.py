"""
Download ERA5 monthly climate data for 2020-2024.

This script downloads temperature and precipitation data from the Copernicus Climate Data Store (CDS).
ERA5 data is licensed under CC-BY 4.0 and free for commercial use.

Before running:
1. Register for a free account at https://cds.climate.copernicus.eu/
2. Install CDS API key by creating ~/.cdsapirc (or %USERPROFILE%/.cdsapirc on Windows) with:
   url: https://cds.climate.copernicus.eu/api/v2
   key: YOUR_UID:YOUR_API_KEY
3. Install dependencies: pip install cdsapi

Usage:
    python scripts/download_era5_data.py
"""

import cdsapi
import os
from pathlib import Path

def download_era5_monthly():
    """Download ERA5 monthly averaged reanalysis data."""
    
    # Create output directory
    output_dir = Path(__file__).parent.parent / 'data' / 'era5' / 'raw'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize CDS API client
    c = cdsapi.Client()
    
    # Years and months to download
    years = ['2020', '2021', '2022', '2023', '2024']
    months = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']
    
    # Variables to download
    # Note: We don't need solar radiation since we use CRU sunshine data
    variables = [
        '2m_temperature',           # For min/max temperature calculation
        'total_precipitation',      # Monthly precipitation
    ]
    
    print("=" * 80)
    print("ERA5 Monthly Data Download")
    print("=" * 80)
    print(f"Years: {', '.join(years)}")
    print(f"Variables: {', '.join(variables)}")
    print(f"Output directory: {output_dir}")
    print("=" * 80)
    
    # Download temperature data
    temp_file = output_dir / 'era5_temperature_monthly_2020-2024.nc'
    if temp_file.exists():
        print(f"\n✓ Temperature file already exists: {temp_file}")
    else:
        print(f"\n→ Downloading 2m temperature data...")
        try:
            c.retrieve(
                'reanalysis-era5-single-levels-monthly-means',
                {
                    'product_type': 'monthly_averaged_reanalysis',
                    'variable': '2m_temperature',
                    'year': years,
                    'month': months,
                    'time': '00:00',
                    'format': 'netcdf',
                },
                str(temp_file)
            )
            print(f"✓ Downloaded: {temp_file}")
        except Exception as e:
            print(f"✗ Error downloading temperature: {e}")
            return False
    
    # Download precipitation data
    prec_file = output_dir / 'era5_precipitation_monthly_2020-2024.nc'
    if prec_file.exists():
        print(f"\n✓ Precipitation file already exists: {prec_file}")
    else:
        print(f"\n→ Downloading total precipitation data...")
        try:
            c.retrieve(
                'reanalysis-era5-single-levels-monthly-means',
                {
                    'product_type': 'monthly_averaged_reanalysis',
                    'variable': 'total_precipitation',
                    'year': years,
                    'month': months,
                    'time': '00:00',
                    'format': 'netcdf',
                },
                str(prec_file)
            )
            print(f"✓ Downloaded: {prec_file}")
        except Exception as e:
            print(f"✗ Error downloading precipitation: {e}")
            return False
    
    print("\n" + "=" * 80)
    print("✓ Download complete!")
    print("=" * 80)
    print(f"\nNext step: Run process_era5_data.py to convert to GeoTIFF format")
    
    return True

if __name__ == '__main__':
    success = download_era5_monthly()
    if not success:
        print("\n⚠ Download failed. Please check:")
        print("  1. CDS API credentials are configured (~/.cdsapirc)")
        print("  2. You have accepted the ERA5 license terms on the CDS website")
        print("  3. Your internet connection is stable")
        exit(1)
