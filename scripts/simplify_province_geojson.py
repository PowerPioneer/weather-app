"""
Simplify province GeoJSON files to reduce file size and improve loading performance.
This script reduces geometry complexity by 5% while maintaining visual quality.
"""
import geopandas as gpd
import json
from pathlib import Path
import time

def simplify_geojson(input_path, output_path, tolerance=0.05):
    """
    Simplify a GeoJSON file using Douglas-Peucker algorithm.
    
    Args:
        input_path: Path to input GeoJSON file
        output_path: Path to output simplified GeoJSON file
        tolerance: Simplification tolerance in degrees (0.05 ≈ 5.5km at equator)
    """
    print(f"Loading {input_path.name}...")
    start_time = time.time()
    
    # Load GeoJSON
    gdf = gpd.read_file(input_path)
    original_size = input_path.stat().st_size / (1024 * 1024)  # MB
    
    print(f"  Original: {original_size:.2f} MB, {len(gdf)} features")
    
    # Simplify geometries
    print(f"  Simplifying with tolerance {tolerance}...")
    gdf['geometry'] = gdf['geometry'].simplify(tolerance=tolerance, preserve_topology=True)
    
    # Round coordinates to 5 decimal places (~1.1m precision)
    # This also reduces file size significantly
    print(f"  Rounding coordinates to 5 decimal places...")
    gdf['geometry'] = gdf['geometry'].apply(
        lambda geom: geom if geom is None else round_coordinates(geom, decimals=5)
    )
    
    # Save simplified GeoJSON
    print(f"  Saving to {output_path.name}...")
    gdf.to_file(output_path, driver='GeoJSON')
    
    # Get output file size
    new_size = output_path.stat().st_size / (1024 * 1024)  # MB
    
    # Calculate reduction
    size_reduction = ((original_size - new_size) / original_size) * 100
    
    elapsed = time.time() - start_time
    
    print(f"  ✓ Complete in {elapsed:.1f}s")
    print(f"    Size: {original_size:.2f} MB → {new_size:.2f} MB ({size_reduction:.1f}% reduction)")
    print()
    
    return new_size, size_reduction

def round_coordinates(geom, decimals=5):
    """Round all coordinates in a geometry to specified decimal places."""
    from shapely.geometry import mapping, shape
    
    geom_json = mapping(geom)
    
    def round_coords(coords):
        """Recursively round coordinates."""
        if isinstance(coords[0], (list, tuple)):
            return [round_coords(c) for c in coords]
        else:
            return [round(c, decimals) for c in coords]
    
    if 'coordinates' in geom_json:
        geom_json['coordinates'] = round_coords(geom_json['coordinates'])
    
    return shape(geom_json)

def main():
    """Simplify all province GeoJSON files."""
    # Paths
    provinces_dir = Path(__file__).parent.parent / "data" / "provinces" / "aggregated"
    
    if not provinces_dir.exists():
        print(f"ERROR: Directory not found: {provinces_dir}")
        return
    
    # Find all province month files
    geojson_files = sorted(provinces_dir.glob("provinces_month_*.geojson"))
    
    if not geojson_files:
        print(f"No province GeoJSON files found in {provinces_dir}")
        return
    
    print(f"Found {len(geojson_files)} province GeoJSON files to simplify")
    print("=" * 70)
    print()
    
    # Create backup directory
    backup_dir = provinces_dir / "backup_original"
    backup_dir.mkdir(exist_ok=True)
    print(f"Backups will be saved to: {backup_dir}")
    print()
    
    total_original_size = 0
    total_new_size = 0
    
    # Process each file
    for geojson_file in geojson_files:
        # Backup original
        backup_path = backup_dir / geojson_file.name
        if not backup_path.exists():
            print(f"Backing up {geojson_file.name}...")
            import shutil
            shutil.copy2(geojson_file, backup_path)
        
        # Simplify and save to same location
        original_size = geojson_file.stat().st_size / (1024 * 1024)
        new_size, reduction = simplify_geojson(geojson_file, geojson_file, tolerance=0.05)
        
        total_original_size += original_size
        total_new_size += new_size
    
    # Summary
    print("=" * 70)
    print(f"SUMMARY")
    print(f"  Files processed: {len(geojson_files)}")
    print(f"  Total original size: {total_original_size:.2f} MB")
    print(f"  Total new size: {total_new_size:.2f} MB")
    print(f"  Total reduction: {((total_original_size - total_new_size) / total_original_size) * 100:.1f}%")
    print(f"  Space saved: {total_original_size - total_new_size:.2f} MB")
    print()
    print(f"✓ All files simplified successfully!")
    print(f"  Original files backed up to: {backup_dir}")

if __name__ == '__main__':
    main()
