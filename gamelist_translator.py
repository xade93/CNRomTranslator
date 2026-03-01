#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import os
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET


def strip_region_suffix(name: str) -> str:
    """Strip region suffixes like (USA), (Japan), etc. from game names"""
    # Remove region/platform info in parentheses at the end
    name = re.sub(r'\s*\([^)]*(?:USA|Japan|Europe|China|Korea|Australia|Canada|PAL|NTSC|Asia|Brazil|Mexico|France|Germany|Italy|Spain|UK|Region|Rev|Disc|CD)[^)]*\)\s*', '', name, flags=re.I)
    # Also remove language info in parentheses  
    name = re.sub(r'\s*\([^)]*(?:En|Fr|De|Es|It)[^)]*\)\s*', '', name, flags=re.I)
    return name.strip()


def load_all_csvs(csv_dir: str) -> dict:
    """
    Load all CSV files and create mapping: English name (without region) -> Chinese name
    Returns a dictionary where key is English name (stripped of region suffixes) and value is Chinese name
    """
    en_to_cn = {}  # English name (no region) -> Chinese name
    
    csv_path = Path(csv_dir)
    if not csv_path.exists():
        print(f"[WARN] CSV directory not found: {csv_dir}", file=sys.stderr)
        return en_to_cn
    
    for csv_file in sorted(csv_path.glob("*.csv")):
        try:
            with open(csv_file, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    continue
                
                # Find the EN and CN column names (case-insensitive)
                keys = {k.strip().lower(): k for k in reader.fieldnames}
                en_col = keys.get("name en")
                cn_col = keys.get("name cn")
                
                if not en_col or not cn_col:
                    continue
                
                for row in reader:
                    en = (row.get(en_col) or "").strip()
                    cn = (row.get(cn_col) or "").strip()
                    
                    # Only store if both EN and CN are non-empty
                    if en and cn:
                        # Strip region suffix from EN name
                        en_stripped = strip_region_suffix(en)
                        # Store the mapping if not already present
                        if en_stripped and en_stripped not in en_to_cn:
                            en_to_cn[en_stripped] = cn
                        
        except Exception as e:
            print(f"[WARN] Error loading {csv_file}: {e}", file=sys.stderr)
    
    return en_to_cn


def main():
    ap = argparse.ArgumentParser(description="Translate game names in gamelist.xml using CSV files")
    ap.add_argument("gamelist", nargs="?", default="./gamelist.xml", 
                    help="Path to gamelist.xml (default: ./gamelist.xml)")
    ap.add_argument("--csv-dir", default="./rom-name-cn", 
                    help="Directory containing CSV files (default: ./rom-name-cn)")
    ap.add_argument("--output", default="./gamelist-translated.xml", 
                    help="Output file path (default: ./gamelist-translated.xml)")
    
    args = ap.parse_args()
    
    # Check if gamelist.xml exists
    if not os.path.isfile(args.gamelist):
        print(f"[ERR] gamelist.xml not found: {args.gamelist}", file=sys.stderr)
        return 1
    
    # Load all CSV mappings: EN -> CN
    print(f"[INFO] Loading CSV files from {args.csv_dir}...", file=sys.stderr)
    en_to_cn = load_all_csvs(args.csv_dir)
    print(f"[INFO] Loaded {len(en_to_cn)} English-Chinese name mappings", file=sys.stderr)
    
    if not en_to_cn:
        print(f"[WARN] No mappings loaded. No translations will be performed.", file=sys.stderr)
    
    # Parse XML
    print(f"[INFO] Parsing {args.gamelist}...", file=sys.stderr)
    try:
        with open(args.gamelist, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove XML declaration if present
        if content.startswith('<?xml'):
            content = content[content.index('?>') + 2:].lstrip()
        
        # Handle malformed XML with multiple root elements by wrapping
        if '</alternativeEmulator>' in content and '<gameList>' in content:
            content = '<root>' + content + '</root>'
        
        root = ET.fromstring(content)
        
        # If we wrapped the content, get the gameList element
        if root.tag == 'root':
            gamelist = root.find('gameList')
            if gamelist is None:
                raise ValueError("Could not find gameList element")
        else:
            gamelist = root
    except Exception as e:
        print(f"[ERR] Failed to parse XML: {e}", file=sys.stderr)
        return 1
    
    # Process all games
    translated_count = 0
    
    for game in gamelist.findall('.//game'):
        name_elem = game.find('name')
        if name_elem is not None and name_elem.text:
            original_en_name = name_elem.text
            
            # Strip region suffix from gamelist name as well for matching
            en_name_stripped = strip_region_suffix(original_en_name)
            
            # Exact match lookup: if English name (stripped) is in CSV, replace with Chinese name
            if en_name_stripped in en_to_cn:
                cn_name = en_to_cn[en_name_stripped]
                print(f"[TRANS] {original_en_name} -> {cn_name}", file=sys.stderr)
                name_elem.text = cn_name
                translated_count += 1
    
    # Write output
    print(f"[INFO] Writing {args.output}...", file=sys.stderr)
    try:
        # Handle wrapping: if we wrapped it, extract just gameList
        if root.tag == 'root':
            output_tree = gamelist
            tree = ET.ElementTree(output_tree)
        else:
            tree = ET.ElementTree(root)
        
        tree.write(args.output, encoding='utf-8', xml_declaration=True, default_namespace=None)
        print(f"[INFO] Translated {translated_count} game names", file=sys.stderr)
        print(f"[INFO] Saved to {args.output}", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"[ERR] Failed to write output: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
