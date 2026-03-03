#!/usr/bin/env python3
"""
Minify JavaScript and CSS assets for production deployment.
Creates .min.js and .min.css versions of static assets.
"""
import rjsmin
import cssmin
from pathlib import Path

STATIC_DIR = Path(__file__).parent.parent / "static"

def minify_js(name="script"):
    """Minify a JavaScript file."""
    js_file = STATIC_DIR / f"{name}.js"
    min_file = STATIC_DIR / f"{name}.min.js"

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

def minify_css(name="style"):
    """Minify a CSS file."""
    css_file = STATIC_DIR / f"{name}.css"
    min_file = STATIC_DIR / f"{name}.min.css"

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

    results = []
    for name in ["script", "onboarding"]:
        results.append(minify_js(name))
        print()
    for name in ["style", "onboarding"]:
        results.append(minify_css(name))
        print()

    print("=" * 50)
    if all(results):
        print("✓ All assets minified successfully")
    else:
        print("⚠ Some assets failed to minify")
    print("=" * 50)

if __name__ == "__main__":
    main()
