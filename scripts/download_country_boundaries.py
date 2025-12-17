"""
Download and prepare country boundaries for climate data aggregation.

This script downloads Natural Earth Admin-0 (countries) boundaries,
which are public domain and suitable for commercial use.

Data Source: Natural Earth (public domain)
URL: https://www.naturalearthdata.com/downloads/10m-cultural-vectors/
License: Public Domain (no restrictions)
"""

import os
import sys
import json
import zipfile
import requests
from pathlib import Path
import geopandas as gpd

# Configuration
NATURAL_EARTH_URL = "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_0_countries.zip"
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "countries"
SHAPEFILE_NAME = "ne_10m_admin_0_countries"


def create_directories():
    """Create necessary directories for country data."""
    print("📁 Creating directory structure...")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ Created: {DATA_DIR}")


def download_boundaries():
    """Download Natural Earth Admin-0 boundaries."""
    zip_path = DATA_DIR / "countries.zip"
    
    if zip_path.exists():
        print(f"✓ ZIP file already exists: {zip_path}")
        return zip_path
    
    print(f"⬇️  Downloading Natural Earth Admin-0 boundaries...")
    print(f"   Source: {NATURAL_EARTH_URL}")
    
    try:
        response = requests.get(NATURAL_EARTH_URL, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    print(f"\r   Progress: {percent:.1f}%", end='')
        
        print(f"\n✓ Downloaded: {zip_path} ({downloaded / 1024 / 1024:.2f} MB)")
        return zip_path
        
    except requests.RequestException as e:
        print(f"❌ Download failed: {e}")
        sys.exit(1)


def extract_boundaries(zip_path):
    """Extract shapefile from ZIP archive."""
    print(f"📦 Extracting shapefile...")
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Extract all files
            zip_ref.extractall(DATA_DIR)
        
        # Verify shapefile exists
        shapefile_path = DATA_DIR / f"{SHAPEFILE_NAME}.shp"
        if not shapefile_path.exists():
            print(f"❌ Shapefile not found: {shapefile_path}")
            sys.exit(1)
        
        print(f"✓ Extracted shapefile: {shapefile_path}")
        return shapefile_path
        
    except zipfile.BadZipFile as e:
        print(f"❌ Invalid ZIP file: {e}")
        sys.exit(1)


def convert_to_geojson(shapefile_path):
    """Convert shapefile to GeoJSON for web use."""
    print(f"🗺️  Converting to GeoJSON...")
    
    try:
        # Read shapefile
        gdf = gpd.read_file(shapefile_path)
        
        # Select relevant columns (reduce file size)
        columns_to_keep = [
            'NAME',           # Country name (use NAME for countries, not 'name')
            'NAME_LONG',      # Long form name
            'ABBREV',         # Abbreviation
            'ISO_A2',         # ISO country code (2-letter)
            'ISO_A3',         # ISO country code (3-letter)
            'CONTINENT',      # Continent
            'REGION_UN',      # UN Region
            'SUBREGION',      # Subregion
            'geometry'        # Geometry
        ]
        
        # Keep only columns that exist
        available_columns = [col for col in columns_to_keep if col in gdf.columns]
        gdf_simplified = gdf[available_columns].copy()
        
        # Rename NAME to name for consistency with province data
        if 'NAME' in gdf_simplified.columns:
            gdf_simplified.rename(columns={'NAME': 'name'}, inplace=True)
        
        # Rename ISO_A2 to iso_a2 for consistency
        if 'ISO_A2' in gdf_simplified.columns:
            gdf_simplified.rename(columns={'ISO_A2': 'iso_a2'}, inplace=True)
        
        # Simplify geometries to reduce file size (tolerance in degrees)
        print("   Simplifying geometries...")
        gdf_simplified['geometry'] = gdf_simplified['geometry'].simplify(tolerance=0.01, preserve_topology=True)
        
        # Save as GeoJSON
        geojson_path = DATA_DIR / "countries.geojson"
        gdf_simplified.to_file(geojson_path, driver='GeoJSON')
        
        file_size = geojson_path.stat().st_size / 1024 / 1024
        print(f"✓ Created GeoJSON: {geojson_path} ({file_size:.2f} MB)")
        print(f"   Total countries: {len(gdf_simplified)}")
        
        return gdf_simplified
        
    except Exception as e:
        print(f"❌ Conversion failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def generate_metadata(gdf):
    """Generate metadata about country boundaries."""
    print(f"📝 Generating metadata...")
    
    try:
        # Count countries by continent
        continent_counts = {}
        if 'CONTINENT' in gdf.columns:
            continent_counts = gdf['CONTINENT'].value_counts().to_dict()
        
        # Get total bounds
        bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
        
        metadata = {
            "source": "Natural Earth",
            "dataset": "Admin-0 Countries",
            "version": "10m (1:10 million scale)",
            "license": "Public Domain",
            "url": "https://www.naturalearthdata.com",
            "commercial_use": True,
            "downloaded_date": "2025-12-17",
            "total_countries": len(gdf),
            "bounds": {
                "west": float(bounds[0]),
                "south": float(bounds[1]),
                "east": float(bounds[2]),
                "north": float(bounds[3])
            },
            "available_attributes": list(gdf.columns),
            "countries_by_continent": continent_counts,
            "files": {
                "shapefile": f"{SHAPEFILE_NAME}.shp",
                "geojson": "countries.geojson",
                "metadata": "metadata.json"
            }
        }
        
        # Save metadata
        metadata_path = DATA_DIR / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Created metadata: {metadata_path}")
        print(f"\n📊 Summary:")
        print(f"   Total countries: {metadata['total_countries']}")
        print(f"   Bounds: ({bounds[1]:.2f}°S to {bounds[3]:.2f}°N, {bounds[0]:.2f}°W to {bounds[2]:.2f}°E)")
        print(f"   License: {metadata['license']} ✓ Commercial use allowed")
        
        return metadata
        
    except Exception as e:
        print(f"❌ Metadata generation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main execution function."""
    print("=" * 70)
    print("Country Boundary Download and Preparation")
    print("=" * 70)
    print()
    
    # Step 1: Create directories
    create_directories()
    print()
    
    # Step 2: Download boundaries
    zip_path = download_boundaries()
    print()
    
    # Step 3: Extract shapefile
    shapefile_path = extract_boundaries(zip_path)
    print()
    
    # Step 4: Convert to GeoJSON
    gdf = convert_to_geojson(shapefile_path)
    print()
    
    # Step 5: Generate metadata
    generate_metadata(gdf)
    print()
    
    print("=" * 70)
    print("✅ Country boundaries successfully downloaded and prepared!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Review files in:", DATA_DIR)
    print("2. Run aggregate_country_data.py to compute country statistics")
    print("3. Update frontend to display country view when zoomed out")
    print()


if __name__ == "__main__":
    main()
