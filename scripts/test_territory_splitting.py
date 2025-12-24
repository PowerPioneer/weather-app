"""
Quick test script to verify territory splitting logic for France and USA.
"""
import geopandas as gpd
from pathlib import Path
import sys

# Add parent directory to path to import from aggregate script
sys.path.insert(0, str(Path(__file__).parent))

from aggregate_country_data import split_country_by_distance, DISTANCE_THRESHOLD_KM

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
COUNTRIES_BASE_DIR = DATA_DIR / "countries"

def test_splitting():
    """Test territory splitting for countries with distant territories."""
    print(f"Testing territory splitting with {DISTANCE_THRESHOLD_KM} km threshold")
    print("=" * 70)
    
    # Load country boundaries
    country_geojson = COUNTRIES_BASE_DIR / "countries.geojson"
    print(f"\nLoading: {country_geojson}")
    country_gdf = gpd.read_file(country_geojson)
    
    # Test specific countries known to have distant territories
    test_countries = ['France', 'United States of America', 'United Kingdom', 
                     'Netherlands', 'Denmark', 'Australia', 'New Zealand']
    
    for country_name in test_countries:
        country_row = country_gdf[country_gdf['name'] == country_name]
        
        if len(country_row) == 0:
            print(f"\n❌ {country_name} not found")
            continue
        
        geom = country_row.iloc[0]['geometry']
        print(f"\n{'='*70}")
        print(f"Testing: {country_name}")
        print(f"{'='*70}")
        
        territories = split_country_by_distance(country_name, geom)
        
        print(f"Split into {len(territories)} territories:")
        for i, (name, geom, area_km2) in enumerate(territories, 1):
            print(f"  {i}. {name}: {area_km2:,.0f} km²")
        
        if len(territories) > 1:
            print(f"\n✓ Successfully split {country_name} into {len(territories)} territories")
        else:
            print(f"\n  No splitting needed for {country_name}")

if __name__ == '__main__':
    test_splitting()
