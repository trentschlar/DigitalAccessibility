"""
Create VisionDeficient24ColorPalette.stylx with colors and accessible symbols
ArcGIS Pro 3.3.2 compatible

SETUP:
1. Create empty .stylx in ArcGIS Pro: Insert > New Style > "VisionDeficient24ColorPalette"
2. Add to project: Insert > Styles > Add Style > Browse to Y:\VisionDeficient24ColorPalette.stylx
3. Run this script in ArcGIS Pro notebook
"""

import arcpy
import os
import sqlite3
import json

# Configuration
style_path = r"Y:\VisionDeficient24ColorPalette.stylx"

# 26 palette colors
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

# ALL 135 accessible contrast pairs
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
    ("FF9DC8","5A000F"), ("00B408","000000"), ("FFCFE2","65019F"), ("009FFA","000000"),
    ("7E0018","00F407"), ("8400CD","FFFFFF"), ("FF5AAF","000000"), ("FF9DC8","450270"),
    ("005745","7CFFFA"), ("5A000F","00D302"), ("00E5F8","7E0018"), ("7E0018","00E5F8"),
    ("00735C","FFFFFF"), ("FF9DC8","7E0018"), ("65019F","00F407"), ("FFCFE2","A40122"),
    ("FFCFE2","8400CD"), ("00C2F9","5A000F"), ("7CFFFA","A40122"), ("A40122","00F407"),
    ("009FFA","5A000F"), ("65019F","00E5F8"), ("FF5AAF","5A000F"), ("5A000F","00B408"),
    ("005745","AFFF2A"), ("003D30","00D302"), ("7CFFFA","8400CD"), ("FF9DC8","65019F"),
    ("FF9DC8","A40122"), ("A40122","AFFF2A"), ("009FFA","450270"), ("009175","FFFFFF"),
    ("450270","00D302"), ("7E0018","00D302"), ("A40122","00E5F8"), ("5A000F","009FFA"),
    ("CD022D","FFFFFF"), ("450270","00B408"), ("00C2F9","7E0018"), ("00C2F9","450270"),
    ("A40122","00D302"), ("8400CD","7CFFFA"), ("FFCFE2","CD022D"), ("FF5AAF","450270"),
    ("7E0018","00B408"), ("FF9DC8","8400CD"), ("8400CD","AFFF2A"), ("009FFA","7E0018"),
    ("7CFFFA","CD022D"), ("5A000F","009175"), ("A40122","00B408"), ("00B408","5A000F"),
    ("00E5F8","A40122"), ("65019F","00D302"), ("00D302","5A000F"), ("AFFF2A","5A000F"),
    ("009FFA","65019F"), ("8400CD","00F407"), ("FF5AAF","7E0018"), ("65019F","00B408"),
    ("00F407","5A000F"), ("009175","7CFFFA"), ("00E5F8","450270"), ("CD022D","7CFFFA"),
    ("8400CD","00E5F8"), ("00C2F9","A40122"), ("AFFF2A","7E0018"), ("00F407","450270"),
    ("FF5AAF","65019F"), ("009175","AFFF2A"), ("AFFF2A","450270"), ("00D302","7E0018"),
    ("00E5F8","8400CD"), ("FF5AAF","A40122"), ("CD022D","AFFF2A"), ("00B408","7E0018"),
    ("00D302","450270"), ("8400CD","00D302"), ("FF5AAF","8400CD"), ("00C2F9","65019F"),
    ("00B408","450270"), ("CD022D","00F407"), ("00C2F9","8400CD"), ("A700FC","FFFFFF"),
    ("009FFA","A40122"), ("009FFA","8400CD"), ("CD022D","00E5F8"), ("00735C","7CFFFA"),
    ("AFFF2A","A40122"), ("00F407","7E0018"), ("00E5F8","CD022D"), ("AFFF2A","65019F"),
    ("00D302","A40122"), ("CD022D","00D302"), ("00735C","AFFF2A"), ("AFFF2A","8400CD"),
    ("00B408","A40122"), ("00E5F8","65019F"), ("005745","00F407"), ("CD022D","00B408"),
    ("00D302","65019F"), ("00B408","65019F"), ("005745","00E5F8"), ("00D302","8400CD"),
    ("00B408","8400CD"), ("005745","00D302"), ("005745","00B408"), ("003D30","00B408")
]

def hex_to_rgb(hex_color):
    """Convert hex to RGB values (0-255)"""
    hex_color = hex_color.lstrip("#")
    return [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]

def create_point_symbol_json(fill_color, outline_color=None):
    """Create JSON for a point symbol"""
    fill_rgb = hex_to_rgb(fill_color)
    
    symbol = {
        "type": "CIMPointSymbol",
        "symbolLayers": [{
            "type": "CIMVectorMarker",
            "enable": True,
            "size": 10.0,
            "frame": {"xmin": -5.0, "ymin": -5.0, "xmax": 5.0, "ymax": 5.0},
            "markerGraphics": [{
                "type": "CIMMarkerGraphic",
                "geometry": {"rings": [[[-5,-5],[-5,5],[5,5],[5,-5],[-5,-5]]]},
                "symbol": {
                    "type": "CIMPolygonSymbol",
                    "symbolLayers": [{
                        "type": "CIMSolidFill",
                        "enable": True,
                        "color": {"type": "CIMRGBColor", "values": fill_rgb + [100]}
                    }]
                }
            }]
        }]
    }
    
    if outline_color:
        outline_rgb = hex_to_rgb(outline_color)
        symbol["symbolLayers"][0]["markerGraphics"][0]["symbol"]["symbolLayers"].append({
            "type": "CIMSolidStroke",
            "enable": True,
            "width": 1.0,
            "color": {"type": "CIMRGBColor", "values": outline_rgb + [100]}
        })
    
    return json.dumps(symbol)

def create_line_symbol_json(color):
    """Create JSON for a line symbol"""
    rgb = hex_to_rgb(color)
    
    symbol = {
        "type": "CIMLineSymbol",
        "symbolLayers": [{
            "type": "CIMSolidStroke",
            "enable": True,
            "width": 2.0,
            "color": {"type": "CIMRGBColor", "values": rgb + [100]}
        }]
    }
    
    return json.dumps(symbol)

def create_polygon_symbol_json(fill_color, outline_color):
    """Create JSON for a polygon symbol"""
    fill_rgb = hex_to_rgb(fill_color)
    outline_rgb = hex_to_rgb(outline_color)
    
    symbol = {
        "type": "CIMPolygonSymbol",
        "symbolLayers": [
            {
                "type": "CIMSolidFill",
                "enable": True,
                "color": {"type": "CIMRGBColor", "values": fill_rgb + [100]}
            },
            {
                "type": "CIMSolidStroke",
                "enable": True,
                "width": 1.0,
                "color": {"type": "CIMRGBColor", "values": outline_rgb + [100]}
            }
        ]
    }
    
    return json.dumps(symbol)

def main():
    """Create the complete style file"""
    
    print("="*80)
    print("VisionDeficient24ColorPalette - Style File Creator")
    print("="*80)
    
    try:
        # Check file exists
        if not os.path.exists(style_path):
            print("\nERROR: Style file not found!")
            print(f"Expected: {style_path}")
            print("\nCreate it in ArcGIS Pro: Insert > New Style")
            return
        
        # Open database
        print(f"\nOpening: {style_path}")
        conn = sqlite3.connect(style_path)
        cursor = conn.cursor()
        
        # Clear existing items (optional - comment out to keep existing)
        cursor.execute("DELETE FROM ITEMS")
        conn.commit()
        print("Cleared existing items")
        
        # Add color symbols
        print(f"\nAdding {len(PALETTE_COLORS)} color symbols...")
        colors_added = 0
        
        for color_hex in PALETTE_COLORS:
            hex_clean = color_hex.lstrip("#").upper()
            name = COLOR_NAMES.get(hex_clean, hex_clean)
            
            symbol_json = create_point_symbol_json(color_hex)
            
            cursor.execute("""
                INSERT INTO ITEMS (CLASS, CATEGORY, NAME, TAGS, CONTENT, KEY)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                3,  # Point Symbol
                'Colors',
                f"Color_{name}",
                'color;palette;vision',
                symbol_json,
                f"COLOR_{hex_clean}"
            ))
            colors_added += 1
            
            if colors_added % 10 == 0:
                print(f"  {colors_added}/{len(PALETTE_COLORS)}...")
        
        conn.commit()
        print(f"✓ Added {colors_added} colors")
        
        # Add contrast pair symbols
        print(f"\nAdding {len(CONTRAST_PAIRS)} accessible contrast pairs...")
        print("  (Creating point, line, and polygon for each)")
        
        pairs_added = 0
        
        for pair in CONTRAST_PAIRS:
            color1 = pair[0]
            color2 = pair[1]
            name1 = COLOR_NAMES.get(color1, color1)
            name2 = COLOR_NAMES.get(color2, color2)
            base_name = f"{name1}_{name2}"
            
            # Point symbol
            point_json = create_point_symbol_json(f"#{color1}", f"#{color2}")
            cursor.execute("""
                INSERT INTO ITEMS (CLASS, CATEGORY, NAME, TAGS, CONTENT, KEY)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                3,
                'VisionDeficient24',
                f"Point_{base_name}",
                'accessible;contrast;point',
                point_json,
                f"POINT_{color1}_{color2}"
            ))
            
            # Line symbol
            line_json = create_line_symbol_json(f"#{color1}")
            cursor.execute("""
                INSERT INTO ITEMS (CLASS, CATEGORY, NAME, TAGS, CONTENT, KEY)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                4,
                'VisionDeficient24',
                f"Line_{base_name}",
                'accessible;contrast;line',
                line_json,
                f"LINE_{color1}_{color2}"
            ))
            
            # Polygon symbol
            poly_json = create_polygon_symbol_json(f"#{color1}", f"#{color2}")
            cursor.execute("""
                INSERT INTO ITEMS (CLASS, CATEGORY, NAME, TAGS, CONTENT, KEY)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                5,
                'VisionDeficient24',
                f"Polygon_{base_name}",
                'accessible;contrast;polygon',
                poly_json,
                f"POLY_{color1}_{color2}"
            ))
            
            pairs_added += 1
            
            if pairs_added % 20 == 0:
                print(f"  {pairs_added}/{len(CONTRAST_PAIRS)}...")
        
        conn.commit()
        print(f"✓ Added {pairs_added} pairs")
        
        # Summary
        cursor.execute("SELECT COUNT(*) FROM ITEMS")
        total = cursor.fetchone()[0]
        
        conn.close()
        
        print("\n" + "="*80)
        print("SUCCESS!")
        print("="*80)
        print(f"\n📁 Style file: {style_path}")
        print(f"\n📊 Summary:")
        print(f"   Colors:   {colors_added}")
        print(f"   Pairs:    {pairs_added}")
        print(f"   Points:   {pairs_added}")
        print(f"   Lines:    {pairs_added}")
        print(f"   Polygons: {pairs_added}")
        print(f"   TOTAL:    {total} items")
        
        print(f"\n🎨 To use in ArcGIS Pro:")
        print("   1. Open symbology for any layer")
        print("   2. Select 'VisionDeficient24ColorPalette' style")
        print("   3. Browse by category: 'Colors' or 'VisionDeficient24'")
        print("   4. All accessible color combinations are ready!")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    result = main()
else:
    print("VisionDeficient24ColorPalette - Style Creator loaded!")
    print("\nTo create the style file, run: main()")
