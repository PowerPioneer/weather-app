"""
Analyze province GeoJSON files to understand the complexity issue with TopoJSON conversion.
"""

import json
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_DIR = Path(__file__).parent.parent
PROVINCES_DIR = BASE_DIR / 'data' / 'provinces' / 'optimized'

def analyze_geojson(filepath):
    """Analyze a GeoJSON file for properties that might cause issues."""
    print(f"\n{'='*60}")
    print(f"Analyzing: {filepath.name}")
    print(f"{'='*60}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Total features: {len(data['features'])}")
    print(f"File size: {filepath.stat().st_size / 1024 / 1024:.2f} MB")
    
    # Analyze feature complexity
    geometry_types = {}
    coord_counts = []
    multi_part_count = 0
    
    for i, feature in enumerate(data['features']):
        geom = feature['geometry']
        geom_type = geom['type']
        
        geometry_types[geom_type] = geometry_types.get(geom_type, 0) + 1
        
        # Count coordinates
        if geom_type == 'Polygon':
            num_coords = sum(len(ring) for ring in geom['coordinates'])
            coord_counts.append(num_coords)
        elif geom_type == 'MultiPolygon':
            multi_part_count += 1
            num_coords = sum(sum(len(ring) for ring in polygon) for polygon in geom['coordinates'])
            coord_counts.append(num_coords)
            
            # Check for very complex MultiPolygons
            if len(geom['coordinates']) > 10:
                print(f"  Feature {i} ({feature['properties'].get('name', 'Unknown')}): "
                      f"{len(geom['coordinates'])} polygons, {num_coords} coordinates")
    
    print(f"\nGeometry types:")
    for gtype, count in geometry_types.items():
        print(f"  {gtype}: {count}")
    
    if coord_counts:
        print(f"\nCoordinate complexity:")
        print(f"  Average coords per feature: {sum(coord_counts)/len(coord_counts):.0f}")
        print(f"  Max coords per feature: {max(coord_counts)}")
        print(f"  Features with >10k coords: {sum(1 for c in coord_counts if c > 10000)}")
        print(f"  Features with >50k coords: {sum(1 for c in coord_counts if c > 50000)}")
    
    print(f"\nMulti-part features: {multi_part_count}")
    
    # Check coordinate dimensions
    sample_feature = data['features'][0]
    sample_geom = sample_feature['geometry']
    if sample_geom['type'] == 'Polygon':
        sample_coord = sample_geom['coordinates'][0][0]
    else:  # MultiPolygon
        sample_coord = sample_geom['coordinates'][0][0][0]
    
    print(f"\nCoordinate sample: {sample_coord}")
    print(f"Coordinate dimensions: {len(sample_coord)} (expected: 2 for [lon, lat])")
    
    if len(sample_coord) > 2:
        print(f"⚠️  WARNING: Coordinates have {len(sample_coord)} dimensions!")
        print(f"   This might include Z (elevation) or M (measure) values")
        print(f"   TopoJSON typically expects 2D coordinates only")
    
    return data


def test_simple_topojson_conversion(data):
    """Test if simple TopoJSON conversion works without topology."""
    import topojson as tp
    
    print(f"\n{'='*60}")
    print("Testing simple TopoJSON conversion (no topology)...")
    print(f"{'='*60}")
    
    try:
        # Try without topology building
        topology = tp.Topology(
            data,
            prequantize=False,  # Disable quantization
            topology=False,     # Skip topology building
        )
        print("✓ Simple conversion successful (no quantization, no topology)")
        return True
    except Exception as e:
        print(f"✗ Simple conversion failed: {e}")
        return False


def test_with_quantization(data):
    """Test if quantization alone works."""
    import topojson as tp
    
    print(f"\n{'='*60}")
    print("Testing with quantization only...")
    print(f"{'='*60}")
    
    try:
        topology = tp.Topology(
            data,
            prequantize=100000,  # Enable quantization
            topology=False,      # Skip topology building
        )
        print("✓ Quantization successful")
        return True
    except Exception as e:
        print(f"✗ Quantization failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False


def test_with_topology(data):
    """Test if full topology building works."""
    import topojson as tp
    
    print(f"\n{'='*60}")
    print("Testing with full topology building...")
    print(f"{'='*60}")
    
    try:
        topology = tp.Topology(
            data,
            prequantize=100000,
            topology=True,
            prevent_oversimplify=True
        )
        print("✓ Full topology building successful")
        return True
    except Exception as e:
        print(f"✗ Topology building failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main analysis function."""
    # Test the problematic file
    problem_file = PROVINCES_DIR / 'provinces_month_09.geojson'
    
    if not problem_file.exists():
        print(f"File not found: {problem_file}")
        return
    
    # Analyze structure
    data = analyze_geojson(problem_file)
    
    # Test different conversion approaches
    test_simple_topojson_conversion(data)
    test_with_quantization(data)
    test_with_topology(data)
    
    print(f"\n{'='*60}")
    print("CONCLUSION")
    print(f"{'='*60}")
    print("\nThe issue is likely caused by one of these:")
    print("1. Very complex MultiPolygon geometries with many parts")
    print("2. Coordinates with Z or M dimensions")
    print("3. Incompatibility between Shapely 2.x and topojson library")
    print("4. Memory/performance issues with topology building on large datasets")


if __name__ == '__main__':
    main()
