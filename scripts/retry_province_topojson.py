"""
Attempt to convert remaining province months with different strategies.
"""

import json
from pathlib import Path
import topojson as tp
import time

BASE_DIR = Path(__file__).parent.parent
PROVINCES_DIR = BASE_DIR / 'data' / 'provinces' / 'optimized'
PROVINCES_TOPO_DIR = BASE_DIR / 'data' / 'provinces' / 'topojson'

def convert_with_retry(month_num):
    """Try multiple strategies to convert a province file."""
    input_file = PROVINCES_DIR / f'provinces_month_{month_num:02d}.geojson'
    output_file = PROVINCES_TOPO_DIR / f'provinces_month_{month_num:02d}.topojson'
    
    if output_file.exists():
        print(f"✓ Month {month_num:02d} already exists, skipping")
        return True
    
    print(f"\n{'='*60}")
    print(f"Converting Month {month_num:02d}")
    print(f"{'='*60}")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        geojson_data = json.load(f)
    
    strategies = [
        ("Full topology with lower quantization", {
            'prequantize': 10000,  # Lower quantization (less precision, faster)
            'topology': True,
            'prevent_oversimplify': False  # Allow simplification
        }),
        ("Topology without oversimplify prevention", {
            'prequantize': 100000,
            'topology': True,
            'prevent_oversimplify': False
        }),
        ("Quantization only (no topology)", {
            'prequantize': 100000,
            'topology': False
        }),
        ("No optimization (just format conversion)", {
            'prequantize': False,
            'topology': False
        }),
    ]
    
    for strategy_name, options in strategies:
        print(f"\nTrying: {strategy_name}")
        print(f"  Options: {options}")
        
        try:
            start_time = time.time()
            topology = tp.Topology(geojson_data, **options)
            elapsed = time.time() - start_time
            
            print(f"  ✓ Conversion successful ({elapsed:.1f}s)")
            
            # Save the file
            topo_dict = topology.to_dict()
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(topo_dict, f, separators=(',', ':'))
            
            # Calculate size reduction
            input_size = input_file.stat().st_size / 1024 / 1024
            output_size = output_file.stat().st_size / 1024 / 1024
            reduction = ((input_size - output_size) / input_size) * 100
            
            print(f"  ✓ Saved: {input_size:.2f} MB → {output_size:.2f} MB ({reduction:.1f}% smaller)")
            return True
            
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"  ✗ Failed: {type(e).__name__}: {str(e)[:100]}")
            continue
    
    print(f"\n❌ All strategies failed for month {month_num:02d}")
    return False


def main():
    """Convert remaining months."""
    print("\n" + "="*60)
    print("Converting Remaining Province Months")
    print("="*60)
    
    # Try months 09-12
    remaining_months = [9, 10, 11, 12]
    
    success_count = 0
    for month in remaining_months:
        if convert_with_retry(month):
            success_count += 1
    
    print(f"\n{'='*60}")
    print(f"Results: {success_count}/{len(remaining_months)} months converted")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
