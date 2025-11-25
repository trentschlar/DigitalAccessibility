import os
from pathlib import Path

# Color palette with names
COLORS = [
    # Group 1
    ("#003D30", "Dark Teal 1"),
    ("#005745", "Dark Teal 2"),
    ("#00735C", "Medium Teal 1"),
    ("#009175", "Medium Teal 2"),
    # Group 2
    ("#EF0096", "Magenta 1"),
    ("#FF5AAF", "Pink 1"),
    ("#FF9DC8", "Pink 2"),
    ("#FFCFE2", "Light Pink"),
    # Group 3
    ("#450270", "Dark Purple 1"),
    ("#65019F", "Dark Purple 2"),
    ("#8400CD", "Purple 1"),
    ("#A700FC", "Purple 2"),
    # Group 4
    ("#009FFA", "Cyan 1"),
    ("#00C2F9", "Cyan 2"),
    ("#00E5F8", "Cyan 3"),
    ("#7CFFFA", "Light Cyan"),
    # Group 5
    ("#5A000F", "Dark Red 1"),
    ("#7E0018", "Dark Red 2"),
    ("#A40122", "Red 1"),
    ("#CD022D", "Red 2"),
    # Group 6
    ("#00B408", "Green 1"),
    ("#00D302", "Green 2"),
    ("#00F407", "Green 3"),
    ("#AFFF2A", "Light Green"),
    # Additional
    ("#000000", "Black"),
    ("#FFFFFF", "White")
]

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple (0-255)"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_luminance(r, g, b):
    """Calculate relative luminance according to WCAG standards"""
    def adjust(c):
        c = c / 255.0
        if c <= 0.03928:
            return c / 12.92
        else:
            return ((c + 0.055) / 1.055) ** 2.4
    
    r_adj = adjust(r)
    g_adj = adjust(g)
    b_adj = adjust(b)
    
    return 0.2126 * r_adj + 0.7152 * g_adj + 0.0722 * b_adj

def calculate_contrast_ratio(color1, color2):
    """Calculate WCAG contrast ratio between two colors"""
    rgb1 = hex_to_rgb(color1)
    rgb2 = hex_to_rgb(color2)
    
    lum1 = rgb_to_luminance(*rgb1)
    lum2 = rgb_to_luminance(*rgb2)
    
    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)
    
    return (lighter + 0.05) / (darker + 0.05)

def get_contrast_rating(ratio):
    """Get WCAG rating for graphical objects (non-text)"""
    # For graphical objects, WCAG 2.1 requires 3:1 minimum
    if ratio >= 7.0:
        return "AAA"  # Exceeds all requirements
    elif ratio >= 4.5:
        return "AA"   # Exceeds graphical + regular text
    elif ratio >= 3.0:
        return "AA18"  # Meets graphical objects standard
    else:
        return "Fail"

def create_contrast_matrix():
    """Create contrast matrix with all color comparisons"""
    matrix = []
    
    for i, (color1, name1) in enumerate(COLORS):
        row = []
        for j, (color2, name2) in enumerate(COLORS):
            if i == j:
                ratio = None  # Same color
            else:
                ratio = calculate_contrast_ratio(color1, color2)
            row.append(ratio)
        matrix.append(row)
    
    return matrix

def get_accessible_pairings(matrix):
    """Get all color pairings that meet accessibility standards"""
    pairings = []
    
    for i, (color1, name1) in enumerate(COLORS):
        for j, (color2, name2) in enumerate(COLORS):
            if i < j:  # Only show each pair once
                ratio = matrix[i][j]
                rating = get_contrast_rating(ratio)
                if rating in ["AA18", "AA", "AAA"]:
                    pairings.append({
                        'color1': color1,
                        'name1': name1,
                        'color2': color2,
                        'name2': name2,
                        'ratio': ratio,
                        'rating': rating
                    })
    
    # Sort by contrast ratio (highest first)
    pairings.sort(key=lambda x: x['ratio'], reverse=True)
    
    return pairings

def generate_html_report(matrix, output_path):
    """Generate HTML report with visual contrast matrix"""
    
    pairings = get_accessible_pairings(matrix)
    
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>VisionDeficient24ColorPalette - Contrast Analysis</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        h1, h2 {
            color: #333;
        }
        .matrix-container {
            overflow-x: auto;
            margin: 20px 0;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        table {
            border-collapse: collapse;
            font-size: 11px;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: center;
            min-width: 60px;
        }
        th {
            background-color: #333;
            color: white;
            font-weight: bold;
            position: sticky;
            top: 0;
            z-index: 10;
        }
        th.row-header {
            background-color: #333;
            color: white;
            text-align: left;
            position: sticky;
            left: 0;
            z-index: 11;
        }
        td.color-cell {
            font-weight: bold;
            font-size: 10px;
            position: relative;
        }
        td.same-color {
            background-color: #e0e0e0;
            color: #999;
        }
        .rating-AAA { background-color: #4CAF50; color: white; }
        .rating-AA { background-color: #8BC34A; color: white; }
        .rating-AA18 { background-color: #FFC107; color: black; }
        .rating-Fail { background-color: #F44336; color: white; }
        
        .color-swatch {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 1px solid #000;
            margin-right: 8px;
            vertical-align: middle;
        }
        .pairings-container {
            background: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .pairing {
            margin: 10px 0;
            padding: 10px;
            border-left: 4px solid #4CAF50;
            background-color: #f9f9f9;
        }
        .pairing-colors {
            display: flex;
            align-items: center;
            margin: 5px 0;
        }
        .legend {
            margin: 20px 0;
            padding: 15px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .legend-item {
            display: inline-block;
            margin-right: 20px;
            padding: 5px 10px;
            border-radius: 3px;
        }
    </style>
</head>
<body>
    <h1>VisionDeficient24ColorPalette - Contrast Analysis</h1>
    
    <div class="legend">
        <h3>WCAG Ratings for Graphical Objects (Non-Text)</h3>
        <span class="legend-item rating-AAA">AAA: &gt;=7.0 (Excellent)</span>
        <span class="legend-item rating-AA">AA: &gt;=4.5 (Very Good)</span>
        <span class="legend-item rating-AA18">AA18: &gt;=3.0 (Good - Minimum)</span>
        <span class="legend-item rating-Fail">Fail: &lt;3.0 (Insufficient)</span>
    </div>
    
    <div class="matrix-container">
        <h2>Contrast Ratio Matrix</h2>
        <p>Each cell shows the contrast ratio between the row color (background) and column color (foreground).</p>
        <table>
            <thead>
                <tr>
                    <th class="row-header">BG \\ FG</th>"""
    
    # Column headers
    for color, name in COLORS:
        html += f'<th><div class="color-swatch" style="background-color: {color};"></div>{name}</th>'
    html += "</tr></thead><tbody>"
    
    # Matrix rows
    for i, (color1, name1) in enumerate(COLORS):
        html += f'<tr><th class="row-header"><div class="color-swatch" style="background-color: {color1};"></div>{name1}</th>'
        for j, ratio in enumerate(matrix[i]):
            if ratio is None:
                html += '<td class="same-color">—</td>'
            else:
                rating = get_contrast_rating(ratio)
                html += f'<td class="color-cell rating-{rating}">{ratio:.2f}<br><small>{rating}</small></td>'
        html += '</tr>'
    
    html += """</tbody></table>
    </div>
    
    <div class="pairings-container">
        <h2>Recommended Color Pairings</h2>
        <p>All color combinations meeting WCAG AA18 or better (&gt;=3.0 contrast ratio) for graphical objects:</p>
"""
    
    for pairing in pairings:
        html += f"""
        <div class="pairing">
            <div class="pairing-colors">
                <div class="color-swatch" style="background-color: {pairing['color1']};"></div>
                <strong>{pairing['name1']}</strong> ({pairing['color1']})
                <span style="margin: 0 10px;">↔</span>
                <div class="color-swatch" style="background-color: {pairing['color2']};"></div>
                <strong>{pairing['name2']}</strong> ({pairing['color2']})
            </div>
            <div>Contrast Ratio: <strong>{pairing['ratio']:.2f}:1</strong> | Rating: <span class="rating-{pairing['rating']}" style="padding: 2px 6px; border-radius: 3px;">{pairing['rating']}</span></div>
        </div>"""
    
    html += f"""
    </div>
    
    <div class="pairings-container">
        <h3>Summary Statistics</h3>
        <p>Total color pairs analyzed: {len(COLORS) * (len(COLORS) - 1) // 2}</p>
        <p>Pairs meeting AA18 or better: {len(pairings)} ({len(pairings) / (len(COLORS) * (len(COLORS) - 1) // 2) * 100:.1f}%)</p>
    </div>
    
</body>
</html>"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✓ HTML report generated: {output_path}")

def display_html_in_notebook(html_content):
    """Display HTML content directly in Jupyter notebook"""
    try:
        from IPython.display import HTML, display
        display(HTML(html_content))
        return True
    except ImportError:
        return False

def main(output_dir=None, display_in_notebook=True):
    """Generate contrast analysis report
    
    Parameters:
    -----------
    output_dir : str, optional
        Directory to save report. 
        Defaults to Documents/ArcGIS/Styles
    display_in_notebook : bool, optional
        Whether to display HTML report in notebook. Default True.
    """
    
    # Set output directory
    if output_dir is None:
        output_dir = os.path.join(os.path.expanduser("~"), "Documents", "ArcGIS", "Styles")
    os.makedirs(output_dir, exist_ok=True)
    
    print("=" * 80)
    print("VisionDeficient24ColorPalette - Contrast Analysis")
    print("=" * 80)
    print(f"\nOutput directory: {output_dir}")
    
    # Create contrast matrix
    print("\nCalculating contrast ratios...")
    matrix = create_contrast_matrix()
    print(f"  ✓ Analyzed {len(COLORS)} colors ({len(COLORS) * (len(COLORS) - 1) // 2} pairs)")
    
    # Get accessible pairings
    pairings = get_accessible_pairings(matrix)
    print(f"  ✓ Found {len(pairings)} accessible pairings (AA18 or better)")
    
    # Generate HTML report
    print("\nGenerating HTML report...")
    html_path = os.path.join(output_dir, "VisionDeficient24ColorPalette_ContrastReport.html")
    generate_html_report(matrix, html_path)
    
    # Display in notebook if requested
    if display_in_notebook:
        print("\nDisplaying contrast report in notebook...")
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        if display_html_in_notebook(html_content):
            print("  ✓ Report displayed below")
        else:
            print("  ⚠ Could not display in notebook (IPython not available)")
            print(f"  → Open HTML file: {html_path}")
    
    print("\n" + "=" * 80)
    print("✓ SUCCESS!")
    print("=" * 80)
    print(f"\n📁 HTML report: {html_path}")
    
    return {
        'html_path': html_path,
        'matrix': matrix,
        'pairings': pairings,
        'success': True
    }

# For notebook execution
if __name__ == "__main__":
    # When run as script
    result = main()
else:
    # When imported in notebook, provide helpful message
    print("VisionDeficient24ColorPalette - Contrast Analysis loaded!")
    print("\nTo generate the contrast report, run:")
    print("  result = main()")
    print("\nOptional parameters:")
    print("  result = main(output_dir='C:/path/to/output')")
    print("  result = main(display_in_notebook=False)")
