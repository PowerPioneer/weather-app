#!/usr/bin/env python3
"""
Minify JavaScript and CSS assets for production deployment.
Creates .min.js and .min.css versions of static assets.
"""
import rjsmin
import cssmin
from pathlib import Path

STATIC_DIR = Path(__file__).parent.parent / "static"

def minify_js():
    """Minify JavaScript files."""
    js_file = STATIC_DIR / "script.js"
    min_file = STATIC_DIR / "script.min.js"
    
    if not js_file.exists():
        print(f"ERROR: {js_file} not found")
        return False
    
    print(f"Minifying {js_file.name}...")
    
    with open(js_file, 'r', encoding='utf-8') as f:
        js_content = f.read()
    
    original_size = len(js_content)
    minified = rjsmin.jsmin(js_content)
    minified_size = len(minified)
    
    with open(min_file, 'w', encoding='utf-8') as f:
        f.write(minified)
    
    reduction = (1 - minified_size / original_size) * 100
    print(f"  Original: {original_size:,} bytes")
    print(f"  Minified: {minified_size:,} bytes")
    print(f"  Reduction: {reduction:.1f}%")
    print(f"  Output: {min_file.name}")
    
    return True

def minify_css():
    """Minify CSS files."""
    css_file = STATIC_DIR / "style.css"
    min_file = STATIC_DIR / "style.min.css"
    
    if not css_file.exists():
        print(f"ERROR: {css_file} not found")
        return False
    
    print(f"Minifying {css_file.name}...")
    
    with open(css_file, 'r', encoding='utf-8') as f:
        css_content = f.read()
    
    original_size = len(css_content)
    minified = cssmin.cssmin(css_content)
    minified_size = len(minified)
    
    with open(min_file, 'w', encoding='utf-8') as f:
        f.write(minified)
    
    reduction = (1 - minified_size / original_size) * 100
    print(f"  Original: {original_size:,} bytes")
    print(f"  Minified: {minified_size:,} bytes")
    print(f"  Reduction: {reduction:.1f}%")
    print(f"  Output: {min_file.name}")
    
    return True

def main():
    print("=" * 50)
    print("Asset Minification")
    print("=" * 50)
    print()
    
    js_ok = minify_js()
    print()
    css_ok = minify_css()
    
    print()
    print("=" * 50)
    if js_ok and css_ok:
        print("✓ All assets minified successfully")
    else:
        print("⚠ Some assets failed to minify")
    print("=" * 50)

if __name__ == "__main__":
    main()
