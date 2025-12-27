"""
Master pipeline script to run the full data processing workflow.

Prerequisites (run once before pipeline):
- download_country_boundaries.py - Download Natural Earth country boundaries
- download_province_boundaries.py - Download Natural Earth province boundaries
- download_era5_data.py - Download ERA5 climate data (raw NetCDF files)
- process_cru_sunshine.py - Process CRU sunshine data (if not already done)

This script executes the main processing pipeline:
1. Process ERA5 NetCDF to GeoTIFF
2. Aggregate province-level data
3. Download travel advisories (U.S. State Department)
4. Aggregate country-level data (includes travel advisory integration)
5. Optimize GeoTIFF files
6. Optimize province GeoJSON files
7. Optimize country GeoJSON files
8. Convert to TopoJSON (optional)

Usage:
    python scripts/run_full_pipeline.py [--skip-aggregation] [--skip-travel-advisories]
"""

import sys
import subprocess
from pathlib import Path
import argparse

SCRIPTS_DIR = Path(__file__).parent
BASE_DIR = SCRIPTS_DIR.parent


def run_script(script_name, description):
    """Run a Python script and handle errors."""
    print("\n" + "="*70)
    print(f"STEP: {description}")
    print("="*70)
    
    script_path = SCRIPTS_DIR / script_name
    
    if not script_path.exists():
        print(f"⚠️  Script not found: {script_path}")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(BASE_DIR),
            check=True,
            capture_output=False
        )
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error in {description}: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error in {description}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run the full data processing pipeline")
    parser.add_argument("--skip-aggregation", action="store_true",
                       help="Skip aggregation steps (jump to optimization)")
    parser.add_argument("--optimization-only", action="store_true",
                       help="Only run optimization steps (requires existing aggregated data)")
    parser.add_argument("--skip-topojson", action="store_true",
                       help="Skip TopoJSON conversion (use regular GeoJSON)")
    parser.add_argument("--skip-travel-advisories", action="store_true",
                       help="Skip downloading travel advisories (use existing data)")
    
    args = parser.parse_args()
    
    print("="*70)
    print("WEATHER DATA PROCESSING PIPELINE")
    print("="*70)
    
    steps_completed = []
    steps_failed = []
    
    # Step 1: Process ERA5 data
    if not args.skip_aggregation and not args.optimization_only:
        if run_script("process_era5_data.py", "Process ERA5 NetCDF to GeoTIFF"):
            steps_completed.append("Process ERA5 Data")
        else:
            steps_failed.append("Process ERA5 Data")
            print("\n❌ Cannot continue without processed ERA5 data")
            return 1
    
    # Step 2: Aggregate province data
    if not args.skip_aggregation and not args.optimization_only:
        if run_script("aggregate_province_data.py", "Aggregate Province-Level Data"):
            steps_completed.append("Aggregate Province Data")
        else:
            steps_failed.append("Aggregate Province Data")
            print("\n⚠️  Province aggregation failed, but continuing...")
    
    # Step 3: Download travel advisories (before country aggregation)
    if not args.skip_travel_advisories and not args.optimization_only:
        if run_script("download_travel_advisories.py", "Download Travel Advisories"):
            steps_completed.append("Download Travel Advisories")
        else:
            steps_failed.append("Download Travel Advisories")
            print("\n⚠️  Travel advisories download failed, country data will use defaults...")
    
    # Step 4: Aggregate country data
    if not args.skip_aggregation and not args.optimization_only:
        if run_script("aggregate_country_data.py", "Aggregate Country-Level Data"):
            steps_completed.append("Aggregate Country Data")
        else:
            steps_failed.append("Aggregate Country Data")
            print("\n⚠️  Country aggregation failed, but continuing...")
    
    # Step 5: Optimize GeoTIFF files (reduce from ~530 MB to ~130 MB)
    if run_script("optimize_geotiffs.py", "Optimize GeoTIFF Files"):
        steps_completed.append("Optimize GeoTIFF Files")
    else:
        steps_failed.append("Optimize GeoTIFF Files")
        print("\n⚠️  GeoTIFF optimization failed")
    
    # Step 6: Optimize province GeoJSON
    if run_script("optimize_province_geojson.py", "Optimize Province GeoJSON Files"):
        steps_completed.append("Optimize Province GeoJSON")
    else:
        steps_failed.append("Optimize Province GeoJSON")
        print("\n⚠️  Province optimization failed")
    
    # Step 7: Optimize country GeoJSON
    if run_script("optimize_country_geojson.py", "Optimize Country GeoJSON Files"):
        steps_completed.append("Optimize Country GeoJSON")
    else:
        steps_failed.append("Optimize Country GeoJSON")
        print("\n⚠️  Country optimization failed")
    
    # Step 8: Convert to TopoJSON (optional)
    if not args.skip_topojson:
        if run_script("convert_to_topojson.py", "Convert to TopoJSON Format"):
            steps_completed.append("Convert to TopoJSON")
        else:
            steps_failed.append("Convert to TopoJSON")
            print("\n⚠️  TopoJSON conversion failed")
    else:
        print("\n⏭️   Skipping TopoJSON conversion (--skip-topojson flag)")
    
    # Summary
    print("\n" + "="*70)
    print("PIPELINE SUMMARY")
    print("="*70)
    
    if steps_completed:
        print(f"\n✅ Completed steps ({len(steps_completed)}):")
        for step in steps_completed:
            print(f"   • {step}")
    
    if steps_failed:
        print(f"\n❌ Failed steps ({len(steps_failed)}):")
        for step in steps_failed:
            print(f"   • {step}")
    
    # Check output directories
    print("\n" + "="*70)
    print("OUTPUT DIRECTORIES")
    print("="*70)
    
    data_dir = BASE_DIR / "data"
    
    dirs_to_check = [
        ("Province Aggregated", data_dir / "provinces" / "aggregated"),
        ("Province Optimized", data_dir / "provinces" / "optimized"),
        ("Country Aggregated", data_dir / "countries" / "aggregated"),
        ("Country Optimized", data_dir / "countries" / "optimized"),
        ("Country TopoJSON", data_dir / "countries" / "topojson"),
    ]
    
    for name, path in dirs_to_check:
        if path.exists():
            files = list(path.glob("*.geojson"))
            total_size = sum(f.stat().st_size for f in files) / (1024 * 1024)
            print(f"✅ {name}: {len(files)} files, {total_size:.2f} MB")
        else:
            print(f"⚠️  {name}: Directory not found")
    
    print("\n" + "="*70)
    
    if steps_failed:
        print("⚠️  Pipeline completed with errors")
        return 1
    else:
        print("✅ Pipeline completed successfully!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
