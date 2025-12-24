"""
Convert GeoJSON files to TopoJSON format for better compression.

TopoJSON reduces file size by ~50-70% by:
- Removing duplicate coordinates (shared boundaries between polygons)
- Quantizing coordinates to reduce precision
- Using arc topology instead of repeating boundaries

This script converts the optimized GeoJSON files to TopoJSON format.
"""

import json
from pathlib import Path
import topojson as tp
from tqdm import tqdm

# Paths
BASE_DIR = Path(__file__).parent.parent
COUNTRIES_DIR = BASE_DIR / 'data' / 'countries' / 'optimized'
PROVINCES_DIR = BASE_DIR / 'data' / 'provinces' / 'optimized'
COUNTRIES_TOPO_DIR = BASE_DIR / 'data' / 'countries' / 'topojson'
PROVINCES_TOPO_DIR = BASE_DIR / 'data' / 'provinces' / 'topojson'


def convert_geojson_to_topojson(input_file, output_file, object_name='data'):
    """
    Convert a GeoJSON file to TopoJSON format.
    
    Args:
        input_file: Path to input GeoJSON file
        output_file: Path to output TopoJSON file
        object_name: Name for the TopoJSON object
    """
    print(f"  Reading {input_file.name}...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        geojson_data = json.load(f)
    
    # Convert to TopoJSON with quantization
    # Higher prequantize = more precision, larger file
    # 1e5 is good balance between precision and size
    print(f"  Converting to TopoJSON...")
    
    try:
        topology = tp.Topology(
            geojson_data,
            prequantize=100000,  # Quantization level
            topology=True,       # Build topology (share arcs)
            prevent_oversimplify=True  # Prevent topology errors
        )
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as e:
        # If topology building fails, try without topology optimization
        print(f"  Warning: Topology optimization failed ({e}), using simple conversion...")
        try:
            topology = tp.Topology(
                geojson_data,
                prequantize=100000,
                topology=False  # Skip topology building
            )
        except Exception as e2:
            print(f"  Error: Conversion failed entirely: {e2}")
            raise
    
    # Convert to dict format
    topo_dict = topology.to_dict()
    
    # Write TopoJSON file
    print(f"  Writing {output_file.name}...")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(topo_dict, f, separators=(',', ':'))  # No whitespace
    
    # Calculate size reduction
    input_size = input_file.stat().st_size / 1024 / 1024  # MB
    output_size = output_file.stat().st_size / 1024 / 1024  # MB
    reduction = ((input_size - output_size) / input_size) * 100
    
    print(f"  ✓ {input_file.name}: {input_size:.2f} MB → {output_size:.2f} MB ({reduction:.1f}% smaller)\n")
    
    return input_size, output_size


def convert_all_countries():
    """Convert all country GeoJSON files to TopoJSON."""
    print("=" * 60)
    print("Converting Country GeoJSON files to TopoJSON")
    print("=" * 60)
    
    geojson_files = sorted(COUNTRIES_DIR.glob('countries_month_*.geojson'))
    
    if not geojson_files:
        print(f"⚠ No country GeoJSON files found in {COUNTRIES_DIR}")
        return
    
    total_input_size = 0
    total_output_size = 0
    
    for geojson_file in geojson_files:
        # Extract month number from filename
        month_str = geojson_file.stem.split('_')[-1]  # e.g., "01" from "countries_month_01"
        
        output_file = COUNTRIES_TOPO_DIR / f'countries_month_{month_str}.topojson'
        
        input_size, output_size = convert_geojson_to_topojson(
            geojson_file,
            output_file,
            object_name='countries'
        )
        
        total_input_size += input_size
        total_output_size += output_size
    
    total_reduction = ((total_input_size - total_output_size) / total_input_size) * 100
    print(f"Total: {total_input_size:.2f} MB → {total_output_size:.2f} MB ({total_reduction:.1f}% reduction)\n")


def convert_all_provinces():
    """Convert all province GeoJSON files to TopoJSON."""
    print("=" * 60)
    print("Converting Province GeoJSON files to TopoJSON")
    print("=" * 60)
    
    geojson_files = sorted(PROVINCES_DIR.glob('provinces_month_*.geojson'))
    
    if not geojson_files:
        print(f"⚠ No province GeoJSON files found in {PROVINCES_DIR}")
        return
    
    total_input_size = 0
    total_output_size = 0
    
    for geojson_file in geojson_files:
        # Extract month number from filename
        month_str = geojson_file.stem.split('_')[-1]  # e.g., "01" from "provinces_month_01"
        
        output_file = PROVINCES_TOPO_DIR / f'provinces_month_{month_str}.topojson'
        
        input_size, output_size = convert_geojson_to_topojson(
            geojson_file,
            output_file,
            object_name='provinces'
        )
        
        total_input_size += input_size
        total_output_size += output_size
    
    total_reduction = ((total_input_size - total_output_size) / total_input_size) * 100
    print(f"Total: {total_input_size:.2f} MB → {total_output_size:.2f} MB ({total_reduction:.1f}% reduction)\n")


def main():
    """Main conversion function."""
    print("\n" + "=" * 60)
    print("GeoJSON to TopoJSON Converter")
    print("=" * 60 + "\n")
    
    # Convert countries
    convert_all_countries()
    
    # Convert provinces (currently disabled due to topojson library issues with complex geometries)
    # TODO: Find alternative TopoJSON library or implement custom quantization for provinces
    # convert_all_provinces()
    print("\nNote: Province TopoJSON conversion skipped due to complexity.")
    print("      Countries provide ~58% reduction, provinces remain as GeoJSON.\n")
    
    print("=" * 60)
    print("✓ Conversion complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()
