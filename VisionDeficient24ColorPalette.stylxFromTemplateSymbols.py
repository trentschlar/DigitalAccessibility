"""
Generate VisionDeficient24ColorPalette.stylx from template symbols
ArcGIS Pro 3.x compatible

SETUP:
1. Create empty .stylx in ArcGIS Pro: Insert > New Style > "VisionDeficient24ColorPalette"
2. Add to project: Insert > Styles > Add Style > Browse to Y:\VisionDeficient24ColorPalette.stylx
3. Ensure template style exists: Y:\TessUniqueSymbols.stylx
4. Run this script in ArcGIS Pro notebook
"""

import sqlite3
import os
import json
import re

# Paths
template_style_path = r"Y:\TessUniqueSymbols.stylx"
output_style_path   = r"Y:\VisionDeficient24ColorPalette.stylx"

# Palette colors and names
PALETTE_COLORS = [
    "#003D30", "#005745", "#00735C", "#009175",
    "#EF0096", "#FF5AAF", "#FF9DC8", "#FFCFE2",
    "#450270", "#65019F", "#8400CD", "#A700FC",
    "#009FFA", "#00C2F9", "#00E5F8", "#7CFFFA",
    "#5A000F", "#7E0018", "#A40122", "#CD022D",
    "#00B408", "#00D302", "#00F407", "#AFFF2A",
    "#000000", "#FFFFFF"
]

COLOR_NAMES = {
    "003D30": "Dark_Teal_1", "005745": "Dark_Teal_2", "00735C": "Medium_Teal_1", "009175": "Medium_Teal_2",
    "EF0096": "Magenta_1", "FF5AAF": "Pink_1", "FF9DC8": "Pink_2", "FFCFE2": "Light_Pink",
    "450270": "Dark_Purple_1", "65019F": "Dark_Purple_2", "8400CD": "Purple_1", "A700FC": "Purple_2",
    "009FFA": "Cyan_1", "00C2F9": "Cyan_2", "00E5F8": "Cyan_3", "7CFFFA": "Light_Cyan",
    "5A000F": "Dark_Red_1", "7E0018": "Dark_Red_2", "A40122": "Red_1", "CD022D": "Red_2",
    "00B408": "Green_1", "00D302": "Green_2", "00F407": "Green_3", "AFFF2A": "Light_Green",
    "000000": "Black", "FFFFFF": "White"
}

# 135 contrast pairs
CONTRAST_PAIRS = [
    ("000000","FFFFFF"), ("7CFFFA","000000"), ("AFFF2A","000000"), ("FFCFE2","000000"),
    ("5A000F","FFFFFF"), ("450270","FFFFFF"), ("00F407","000000"), ("00E5F8","000000"),
    ("003D30","FFFFFF"), ("7CFFFA","5A000F"), ("5A000F","AFFF2A"), ("450270","7CFFFA"),
    ("450270","AFFF2A"), ("7E0018","FFFFFF"), ("FF9DC8","000000"), ("FFCFE2","5A000F"),
    ("00D302","000000"), ("003D30","7CFFFA"), ("FFCFE2","450270"), ("65019F","FFFFFF"),
    ("00C2F9","000000"), ("003D30","AFFF2A"), ("5A000F","00F407"), ("00E5F8","5A000F"),
    ("450270","00F407"), ("7CFFFA","7E0018"), ("450270","00E5F8"), ("7E0018","AFFF2A"),
    ("003D30","FFCFE2"), ("005745","FFFFFF"), ("65019F","7CFFFA"), ("65019F","AFFF2A"),
    ("003D30","00F407"), ("A40122","FFFFFF"), ("FFCFE2","7E0018"), ("003D30","00E5F8"),
    ("FF5AAF","000000"), ("00B408","000000"), ("009FFA","000000"), ("00C2F9","5A000F"),
    ("5A000F","00E5F8"), ("00E5F8","450270"), ("7E0018","00F407"), ("7CFFFA","A40122"),
    ("450270","FFCFE2"), ("AFFF2A","5A000F"), ("005745","7CFFFA"), ("8400CD","FFFFFF"),
    ("00E5F8","7E0018"), ("003D30","00D302"), ("00C2F9","450270"), ("5A000F","00D302"),
    ("65019F","FFCFE2"), ("005745","AFFF2A"), ("A40122","7CFFFA"), ("00735C","FFFFFF"),
    ("5A000F","FF9DC8"), ("450270","00D302"), ("A40122","AFFF2A"), ("7E0018","00E5F8"),
    ("003D30","FF9DC8"), ("A700FC","FFFFFF"), ("00C2F9","7E0018"), ("A40122","00E5F8"),
    ("005745","00F407"), ("65019F","00F407"), ("7E0018","00D302"), ("A40122","00F407"),
    ("5A000F","00C2F9"), ("450270","00C2F9"), ("003D30","00C2F9"), ("7CFFFA","CD022D"),
    ("005745","00E5F8"), ("65019F","00E5F8"), ("AFFF2A","7E0018"), ("7E0018","00C2F9"),
    ("009175","FFFFFF"), ("A40122","00D302"), ("AFFF2A","A40122"), ("CD022D","FFFFFF"),
    ("FFCFE2","A40122"), ("00735C","7CFFFA"), ("00735C","AFFF2A"), ("5A000F","009FFA"),
    ("450270","009FFA"), ("FFCFE2","CD022D"), ("8400CD","7CFFFA"), ("8400CD","AFFF2A"),
    ("5A000F","00B408"), ("450270","00B408"), ("003D30","009FFA"), ("EF0096","FFFFFF"),
    ("005745","00D302"), ("7E0018","009FFA"), ("A40122","00C2F9"), ("00735C","00F407"),
    ("65019F","00D302"), ("CD022D","7CFFFA"), ("A40122","009FFA"), ("00735C","00E5F8"),
    ("8400CD","00F407"), ("7E0018","009FFA"), ("CD022D","AFFF2A"), ("7CFFFA","EF0096"),
    ("8400CD","00E5F8"), ("003D30","00B408"), ("005745","00C2F9"), ("A700FC","7CFFFA"),
    ("A700FC","AFFF2A"), ("00735C","00D302"), ("65019F","00C2F9"), ("A40122","00B408"),
    ("AFFF2A","CD022D"), ("5A000F","009175"), ("009175","7CFFFA"), ("450270","009175"),
    ("009175","AFFF2A"), ("8400CD","00D302"), ("005745","009FFA"), ("009FFA","5A000F"),
    ("009FFA","450270"), ("00E5F8","CD022D"), ("CD022D","00F407"), ("A700FC","00F407"),
    ("FFCFE2","EF0096"), ("009175","00F407"), ("00735C","00C2F9"), ("A700FC","00E5F8"),
    ("009175","00E5F8"), ("8400CD","00C2F9"), ("CD022D","00E5F8"), ("EF0096","7CFFFA"),
    ("EF0096","AFFF2A"), ("009175","00D302"), ("65019F","009FFA"), ("00C2F9","CD022D"),
    ("005745","00B408"), ("CD022D","00D302"), ("00D302","5A000F"), ("00D302","450270"),
    ("A700FC","00D302"), ("7E0018","009175"), ("00C2F9","EF0096"), ("A40122","009175"),
    ("009175","00C2F9"), ("8400CD","009FFA"), ("CD022D","00C2F9"), ("00735C","009FFA"),
    ("AFFF2A","EF0096")
]

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]

def parse_json_content(content):
    """
    Try to parse JSON content, handling multiple JSON objects or malformed data
    """
    # First, try standard JSON parsing
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        # If that fails, try to extract the first valid JSON object
        try:
            # Find the first complete JSON object using brace matching
            brace_count = 0
            start_pos = -1
            
            for i, char in enumerate(content):
                if char == '{':
                    if brace_count == 0:
                        start_pos = i
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and start_pos >= 0:
                        # Found a complete JSON object
                        json_str = content[start_pos:i+1]
                        return json.loads(json_str)
            
            # If we get here, no valid JSON was found
            raise ValueError("No valid JSON object found in content")
        except Exception as parse_error:
            print(f"ERROR parsing JSON: {parse_error}")
            return None

def replace_colors_in_json(symbol_json, color1, color2):
    """Replace all colors in the JSON with a two-color pair"""
    try:
        symbol = parse_json_content(symbol_json)
        if symbol is None:
            return symbol_json
        
        color_index = [0]  # Use list to maintain state across recursive calls
        
        def replace_in_dict(d, parent_key=None):
            for k, v in d.items():
                if isinstance(v, dict):
                    replace_in_dict(v, k)
                elif isinstance(v, list):
                    # Handle nested lists
                    for item in v:
                        if isinstance(item, dict):
                            replace_in_dict(item, k)
                
                # Handle color values
                if k == "values" and isinstance(v, list) and len(v) == 4:
                    # Check if this is a color property by looking at parent context
                    is_outline = parent_key and ('outline' in str(parent_key).lower() or 
                                                 'border' in str(parent_key).lower() or
                                                 'stroke' in str(parent_key).lower())
                    
                    # Alternate between color1 and color2 for polygons
                    # Use color1 for fill/first color, color2 for outline/second color
                    if is_outline or color_index[0] % 2 == 1:
                        d[k] = hex_to_rgb(color2) + [v[3]]
                    else:
                        d[k] = hex_to_rgb(color1) + [v[3]]
                    
                    color_index[0] += 1
        
        replace_in_dict(symbol)
        return json.dumps(symbol)
    except Exception as e:
        print(f"ERROR replacing colors: {e}")
        return symbol_json

def generate_symbols():
    print("="*80)
    print("VisionDeficient24ColorPalette - Generate symbols from template")
    print("="*80)

    if not os.path.exists(template_style_path):
        print(f"Template style not found: {template_style_path}")
        return
    if not os.path.exists(output_style_path):
        print(f"Output style not found: {output_style_path}")
        return

    # Check for duplicate pairs
    unique_pairs = list(dict.fromkeys(CONTRAST_PAIRS))
    if len(unique_pairs) != len(CONTRAST_PAIRS):
        duplicates = len(CONTRAST_PAIRS) - len(unique_pairs)
        print(f"⚠ Warning: Found {duplicates} duplicate pair(s) - removing duplicates")
        print(f"  Original pairs: {len(CONTRAST_PAIRS)}")
        print(f"  Unique pairs: {len(unique_pairs)}")
        # Find and show the duplicates
        seen = set()
        for pair in CONTRAST_PAIRS:
            if pair in seen:
                print(f"  Duplicate: {pair} ({COLOR_NAMES.get(pair[0], pair[0])} + {COLOR_NAMES.get(pair[1], pair[1])})")
            seen.add(pair)
        print()

    # Open template and output style SQLite databases
    template_conn = sqlite3.connect(template_style_path)
    template_cursor = template_conn.cursor()

    output_conn = sqlite3.connect(output_style_path)
    output_cursor = output_conn.cursor()

    # Clear existing items in output style
    output_cursor.execute("DELETE FROM ITEMS")
    output_conn.commit()
    print("Cleared existing items in output style")

    # Read template symbols
    template_cursor.execute("SELECT CLASS, CATEGORY, NAME, TAGS, CONTENT, KEY FROM ITEMS")
    template_items = template_cursor.fetchall()
    print(f"Loaded template symbols: {len(template_items)} items")

    pairs_added = 0
    total_symbols_created = 0
    
    # Use unique pairs only
    for color1, color2 in unique_pairs:
        for cls, cat, name, tags, content, key in template_items:
            new_name = f"{name}_{COLOR_NAMES.get(color1,color1)}_{COLOR_NAMES.get(color2,color2)}"
            new_key  = f"{key}_{color1}_{color2}"
            new_content = replace_colors_in_json(content, color1, color2)
            
            try:
                output_cursor.execute("""
                    INSERT INTO ITEMS (CLASS, CATEGORY, NAME, TAGS, CONTENT, KEY)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (cls, 'VisionDeficient24', new_name, tags, new_content, new_key))
                total_symbols_created += 1
            except sqlite3.Error as db_error:
                print(f"Database error inserting {new_name}: {db_error}")
        
        pairs_added += 1
        if pairs_added % 10 == 0:
            print(f"  {pairs_added}/{len(unique_pairs)} contrast pairs processed... ({total_symbols_created} symbols created)")

    output_conn.commit()
    template_conn.close()
    output_conn.close()

    print(f"\n✓ Generated {pairs_added} contrast pairs from template symbols")
    print(f"✓ Total symbols created: {total_symbols_created}")
    print("="*80)

if __name__ == "__main__":
    generate_symbols()
