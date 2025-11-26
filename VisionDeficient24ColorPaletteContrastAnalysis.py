import os
from pathlib import Path
import colorsys

# Color palette with names
COLORS = [
    ("#560133", "Mulberry"),
    ("#005745", "Deep Opal"),
    ("#9F0162", "Jazzberry Jam"),
    ("#009175", "Elf Green"),
    ("#EF0096", "Persian Rose"),
    ("#00CBA7", "Aquamarine"),
    ("#FF9DC8", "Amaranth Pink"),
    ("#86FFDE", "Light Turquoise"),
    ("#450270", "Christalle"),
    ("#00489E", "Tory Blue"),
    ("#8400CD", "French Violet"),
    ("#0079FA", "Azure"),
    ("#DA00FD", "Psychedelic Purple"),
    ("#00C2F9", "Capri"),
    ("#FF92FD", "Violet"),
    ("#7CFFFA", "Electric Blue"),
    ("#004002", "British Racing Green"),
    ("#7E0018", "Hot Chile"),
    ("#007702", "Bilbao"),
    ("#CD022D", "Amaranth Red"),
    ("#00B408", "Kelly Green"),
    ("#FF6E3A", "Burning Orange"),
    ("#00F407", "Radioactive Green"),
    ("#FFDC3D", "Gargoyle Gas"),
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

def simulate_color_blindness(r, g, b, cb_type):
    """
    Simulate color blindness using Brettel, Viénot and Mollon (1997) matrices
    
    cb_type: 'deuteranopia', 'protanopia', or 'tritanopia'
    """
    # Normalize RGB to 0-1
    r, g, b = r/255.0, g/255.0, b/255.0
    
    # Transformation matrices for different types of color blindness
    # Based on Brettel, Viénot and Mollon (1997)
    
    if cb_type == 'deuteranopia':  # Green-blind (most common, ~6% of males)
        # Deuteranopia simulation matrix
        sim_r = 0.625 * r + 0.375 * g + 0.0 * b
        sim_g = 0.7 * r + 0.3 * g + 0.0 * b
        sim_b = 0.0 * r + 0.3 * g + 0.7 * b
    
    elif cb_type == 'protanopia':  # Red-blind (~2% of males)
        # Protanopia simulation matrix
        sim_r = 0.567 * r + 0.433 * g + 0.0 * b
        sim_g = 0.558 * r + 0.442 * g + 0.0 * b
        sim_b = 0.0 * r + 0.242 * g + 0.758 * b
    
    elif cb_type == 'tritanopia':  # Blue-blind (very rare, ~0.001%)
        # Tritanopia simulation matrix
        sim_r = 0.95 * r + 0.05 * g + 0.0 * b
        sim_g = 0.0 * r + 0.433 * g + 0.567 * b
        sim_b = 0.0 * r + 0.475 * g + 0.525 * b
    
    else:
        return (r * 255, g * 255, b * 255)
    
    # Convert back to 0-255
    return (int(sim_r * 255), int(sim_g * 255), int(sim_b * 255))

def calculate_cb_contrast_ratio(color1, color2, cb_type):
    """Calculate contrast ratio as seen by someone with color blindness"""
    rgb1 = hex_to_rgb(color1)
    rgb2 = hex_to_rgb(color2)
    
    # Simulate color blindness
    sim_rgb1 = simulate_color_blindness(*rgb1, cb_type)
    sim_rgb2 = simulate_color_blindness(*rgb2, cb_type)
    
    # Calculate luminance of simulated colors
    lum1 = rgb_to_luminance(*sim_rgb1)
    lum2 = rgb_to_luminance(*sim_rgb2)
    
    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)
    
    return (lighter + 0.05) / (darker + 0.05)

def get_cb_accessible(pairings):
    """
    Filter pairings to only those accessible to all color blind types
    Returns: (accessible_pairs, cb_analysis)
    """
    cb_accessible = []
    cb_analysis = []
    
    for pairing in pairings:
        # Calculate contrast for each type of color blindness
        deuter_ratio = calculate_cb_contrast_ratio(pairing['color1'], pairing['color2'], 'deuteranopia')
        prota_ratio = calculate_cb_contrast_ratio(pairing['color1'], pairing['color2'], 'protanopia')
        trita_ratio = calculate_cb_contrast_ratio(pairing['color1'], pairing['color2'], 'tritanopia')
        
        # Check if all types meet AA18 standard (3.0+)
        deuter_pass = deuter_ratio >= 3.0
        prota_pass = prota_ratio >= 3.0
        trita_pass = trita_ratio >= 3.0
        all_pass = deuter_pass and prota_pass and trita_pass
        
        analysis = {
            'color1': pairing['color1'],
            'name1': pairing['name1'],
            'color2': pairing['color2'],
            'name2': pairing['name2'],
            'normal_ratio': pairing['ratio'],
            'normal_rating': pairing['rating'],
            'deuteranopia_ratio': deuter_ratio,
            'deuteranopia_pass': deuter_pass,
            'protanopia_ratio': prota_ratio,
            'protanopia_pass': prota_pass,
            'tritanopia_ratio': trita_ratio,
            'tritanopia_pass': trita_pass,
            'all_cb_pass': all_pass
        }
        
        cb_analysis.append(analysis)
        
        if all_pass:
            cb_accessible.append(pairing)
    
    return cb_accessible, cb_analysis

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
    """Generate HTML report with visual contrast matrix and color blindness analysis"""
    
    pairings = get_accessible_pairings(matrix)
    cb_accessible, cb_analysis = get_cb_accessible(pairings)
    
    # Calculate percentages
    total_pairs = len(COLORS) * (len(COLORS) - 1) // 2
    cb_count = len(cb_accessible)
    normal_count = len(pairings)
    
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>VisionDeficient24ColorPalette - Contrast Analysis</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        h1, h2 {{
            color: #333;
        }}
        .matrix-container {{
            overflow-x: auto;
            margin: 20px 0;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        table {{
            border-collapse: collapse;
            font-size: 11px;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: center;
            min-width: 60px;
        }}
        th {{
            background-color: #333;
            color: white;
            font-weight: bold;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        th.row-header {{
            background-color: #333;
            color: white;
            text-align: left;
            position: sticky;
            left: 0;
            z-index: 11;
        }}
        td.color-cell {{
            font-weight: bold;
            font-size: 10px;
            position: relative;
        }}
        td.same-color {{
            background-color: #e0e0e0;
            color: #999;
        }}
        .rating-AAA {{ background-color: #4CAF50; color: white; }}
        .rating-AA {{ background-color: #8BC34A; color: white; }}
        .rating-AA18 {{ background-color: #FFC107; color: black; }}
        .rating-Fail {{ background-color: #F44336; color: white; }}
        
        .color-swatch {{
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 1px solid #000;
            margin-right: 8px;
            vertical-align: middle;
        }}
        .pairings-container {{
            background: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .pairing {{
            margin: 10px 0;
            padding: 10px;
            border-left: 4px solid #4CAF50;
            background-color: #f9f9f9;
        }}
        .pairing.cb-accessible {{
            border-left-color: #2196F3;
            background-color: #E3F2FD;
        }}
        .pairing-colors {{
            display: flex;
            align-items: center;
            margin: 5px 0;
        }}
        .cb-status {{
            margin-top: 5px;
            font-size: 0.9em;
        }}
        .cb-pass {{
            color: #4CAF50;
            font-weight: bold;
        }}
        .cb-fail {{
            color: #F44336;
        }}
        .legend {{
            margin: 20px 0;
            padding: 15px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .legend-item {{
            display: inline-block;
            margin-right: 20px;
            padding: 5px 10px;
            border-radius: 3px;
        }}
        .cb-info {{
            background: #E3F2FD;
            padding: 15px;
            margin: 20px 0;
            border-radius: 8px;
            border-left: 4px solid #2196F3;
        }}
        .code-output {{
            background: #263238;
            color: #AEDCF5;
            padding: 15px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            overflow-x: auto;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <h1>VisionDeficient24ColorPalette - Contrast Analysis</h1>
    
    <div class="cb-info">
        <h3>🔍 Color Blindness Analysis</h3>
        <p>This palette has been analyzed for accessibility with:</p>
        <ul>
            <li><strong>Deuteranopia</strong> (Green-blind, ~6% of males)</li>
            <li><strong>Protanopia</strong> (Red-blind, ~2% of males)</li>
            <li><strong>Tritanopia</strong> (Blue-blind, ~0.001% of population)</li>
        </ul>
        <p><strong>{cb_count} of {normal_count} pairings</strong> are accessible to ALL color vision types (including color blindness).</p>
    </div>
    
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
                    <th class="row-header">BG \\\\ FG</th>""".format(
        cb_count=cb_count,
        normal_count=normal_count
    )
    
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
        <h2>🎨 Color Blindness Accessible Pairings</h2>
        <p>Pairings that meet WCAG AA18 standard (≥3.0) for <strong>normal vision AND all color blindness types</strong>:</p>
"""
    
    for analysis in cb_analysis:
        if analysis['all_cb_pass']:
            html += f"""
        <div class="pairing cb-accessible">
            <div class="pairing-colors">
                <div class="color-swatch" style="background-color: {analysis['color1']};"></div>
                <strong>{analysis['name1']}</strong> ({analysis['color1']})
                <span style="margin: 0 10px;">↔</span>
                <div class="color-swatch" style="background-color: {analysis['color2']};"></div>
                <strong>{analysis['name2']}</strong> ({analysis['color2']})
            </div>
            <div>Normal Vision: <strong>{analysis['normal_ratio']:.2f}:1</strong> | Rating: <span class="rating-{analysis['normal_rating']}" style="padding: 2px 6px; border-radius: 3px;">{analysis['normal_rating']}</span></div>
            <div class="cb-status">
                <span class="cb-pass">✓ Deuteranopia: {analysis['deuteranopia_ratio']:.2f}:1</span> |
                <span class="cb-pass">✓ Protanopia: {analysis['protanopia_ratio']:.2f}:1</span> |
                <span class="cb-pass">✓ Tritanopia: {analysis['tritanopia_ratio']:.2f}:1</span>
            </div>
        </div>"""
    
    html += """
    </div>
    
    <div class="pairings-container">
        <h2>📋 All Accessible Pairings (Normal Vision)</h2>
        <p>All {count} color combinations meeting WCAG AA18 or better (≥3.0) for normal vision:</p>
    """.format(count=len(pairings))
    
    for analysis in cb_analysis:
        cb_class = "cb-accessible" if analysis['all_cb_pass'] else ""
        cb_indicator = "🟢 " if analysis['all_cb_pass'] else ""
        
        html += f"""
        <div class="pairing {cb_class}">
            <div class="pairing-colors">
                {cb_indicator}<div class="color-swatch" style="background-color: {analysis['color1']};"></div>
                <strong>{analysis['name1']}</strong> ({analysis['color1']})
                <span style="margin: 0 10px;">↔</span>
                <div class="color-swatch" style="background-color: {analysis['color2']};"></div>
                <strong>{analysis['name2']}</strong> ({analysis['color2']})
            </div>
            <div>Normal Vision: <strong>{analysis['normal_ratio']:.2f}:1</strong> | Rating: <span class="rating-{analysis['normal_rating']}" style="padding: 2px 6px; border-radius: 3px;">{analysis['normal_rating']}</span></div>
            <div class="cb-status">
                <span class="{'cb-pass' if analysis['deuteranopia_pass'] else 'cb-fail'}">{'✓' if analysis['deuteranopia_pass'] else '✗'} Deuteranopia: {analysis['deuteranopia_ratio']:.2f}:1</span> |
                <span class="{'cb-pass' if analysis['protanopia_pass'] else 'cb-fail'}">{'✓' if analysis['protanopia_pass'] else '✗'} Protanopia: {analysis['protanopia_ratio']:.2f}:1</span> |
                <span class="{'cb-pass' if analysis['tritanopia_pass'] else 'cb-fail'}">{'✓' if analysis['tritanopia_pass'] else '✗'} Tritanopia: {analysis['tritanopia_ratio']:.2f}:1</span>
            </div>
        </div>"""
    
    html += f"""
    </div>
    
    <div class="pairings-container">
        <h3>📊 Summary Statistics</h3>
        <p>Total color pairs analyzed: {len(COLORS) * (len(COLORS) - 1) // 2}</p>
        <p>Pairs meeting AA18+ (normal vision): {len(pairings)} ({len(pairings) / (len(COLORS) * (len(COLORS) - 1) // 2) * 100:.1f}%)</p>
        <p><strong>Pairs accessible to ALL (including color blindness): {len(cb_accessible)} ({len(cb_accessible) / (len(COLORS) * (len(COLORS) - 1) // 2) * 100:.1f}%)</strong></p>
    </div>
    
    <div class="pairings-container">
        <h2>💻 Python Code for Style Creator</h2>
        <p>Copy this list to update the CONTRAST_PAIRS in the ArcGIS Pro Style File Creator:</p>
        <div class="code-output">
# Color blindness accessible pairs ({len(cb_accessible)} pairs)
CONTRAST_PAIRS_CB_SAFE = [
"""
    
    # Generate Python tuple list for CB-safe pairs
    for i, analysis in enumerate(cb_analysis):
        if analysis['all_cb_pass']:
            color1_clean = analysis['color1'].lstrip('#').upper()
            color2_clean = analysis['color2'].lstrip('#').upper()
            html += f'    ("{color1_clean}", "{color2_clean}")'
            if i < len([a for a in cb_analysis if a['all_cb_pass']]) - 1:
                html += ','
            html += '\n'
    
    html += """]

# All accessible pairs - normal vision ({len(pairings)} pairs)  
CONTRAST_PAIRS_ALL = [
"""
    
    for i, analysis in enumerate(cb_analysis):
        color1_clean = analysis['color1'].lstrip('#').upper()
        color2_clean = analysis['color2'].lstrip('#').upper()
        html += f'    ("{color1_clean}", "{color2_clean}")'
        if i < len(cb_analysis) - 1:
            html += ','
        html += '\n'
    
    html += """]
        </div>
    </div>
    
</body>
</html>""".format(len=len)
    
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
    
    # Analyze color blindness accessibility
    print(f"\nAnalyzing color blindness accessibility...")
    cb_accessible, cb_analysis = get_cb_accessible(pairings)
    print(f"  ✓ Deuteranopia (green-blind) simulated")
    print(f"  ✓ Protanopia (red-blind) simulated")
    print(f"  ✓ Tritanopia (blue-blind) simulated")
    print(f"  ✓ {len(cb_accessible)} pairs accessible to ALL vision types")
    
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
