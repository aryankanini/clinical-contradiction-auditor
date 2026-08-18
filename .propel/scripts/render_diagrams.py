#!/usr/bin/env python
"""Render PlantUML diagrams to PNG using online service."""

import base64
import json
import os
import sys
from pathlib import Path
import urllib.request
import urllib.error

def render_plantuml_diagram(puml_file: Path, output_dir: Path) -> bool:
    """Render a single PlantUML file to PNG using Kroki online renderer."""
    try:
        # Read PlantUML source
        source = puml_file.read_text(encoding='utf-8')
        
        # For Kroki, we can send POST request with JSON payload
        import json
        
        payload = json.dumps({'diagram_source': source}).encode('utf-8')
        
        # Build request for Kroki service (supports PlantUML)
        url = "https://kroki.io/plantuml/png"
        
        # Download rendered image
        output_file = output_dir / puml_file.stem
        output_file = output_file.with_suffix('.png')
        
        try:
            req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=10) as response:
                with open(str(output_file), 'wb') as f:
                    f.write(response.read())
            print(f"✓ Rendered {puml_file.name} → {output_file.name}")
            return True
        except urllib.error.URLError as e:
            print(f"✗ Failed to render {puml_file.name}: {e}")
            # Try alternative method with URL encoding
            try:
                encoded = base64.b64encode(source.encode('utf-8')).decode('ascii')
                url_alt = f"https://www.plantuml.com/plantuml/png/{encoded}"
                urllib.request.urlretrieve(url_alt, str(output_file), timeout=10)
                print(f"✓ Rendered {puml_file.name} → {output_file.name} (fallback)")
                return True
            except Exception as e2:
                print(f"✗ Fallback also failed: {e2}")
                return False
            
    except Exception as e:
        print(f"✗ Error processing {puml_file.name}: {e}")
        return False

def main():
    """Main entry point."""
    uml_dir = Path('d:\\Hackatheon\\clinical-contradiction-auditor\\.propel\\uml')
    
    if not uml_dir.exists():
        print(f"UML directory not found: {uml_dir}")
        return 1
    
    # Find all PlantUML files
    puml_files = sorted(uml_dir.glob('*.puml'))
    
    if not puml_files:
        print(f"No PlantUML files found in {uml_dir}")
        return 1
    
    print(f"Found {len(puml_files)} diagram(s) to render...")
    
    # Render each diagram
    success_count = 0
    for puml_file in puml_files:
        if render_plantuml_diagram(puml_file, uml_dir):
            success_count += 1
    
    print(f"\nRendered {success_count}/{len(puml_files)} diagram(s) successfully")
    return 0 if success_count == len(puml_files) else 1

if __name__ == '__main__':
    sys.exit(main())
