# -*- coding: utf-8 -*-
import pandas as pd
import json
from datetime import date
import re

# --- List of CSV files ---
csv_files = [
    r"Y:\LayerAudit\Baseline Audits\OSMP_Baseline_Layers_20251117_082710.csv",
    r"Y:\LayerAudit\Baseline Audits\OSMP_Baseline_Layers_20251117_083415.csv",
    r"Y:\LayerAudit\Baseline Audits\OSMP_Baseline_Layers_20251117_083512.csv",
    r"Y:\LayerAudit\Baseline Audits\OSMP_Baseline_Layers_20251117_084921.csv",
    r"Y:\LayerAudit\Baseline Audits\OSMP_Baseline_OSMP_Dog_Regs_Map_(WAB)_20251117_082511.csv",
    r"Y:\LayerAudit\Baseline Audits\OSMP_Baseline_OSMP_Horse_Regulations_(WAB)_20251114_161708.csv",
    r"Y:\LayerAudit\Baseline Audits\OSMP_Baseline_Wildlife_Closures_Current_PUBLIC_(WAB)_20251117_083237.csv",
    r"Y:\LayerAudit\Baseline Audits\OSMP_Baseline_OSMP_Trail_Map_(WAB)_20251117_090840.csv"
]

# --- Contrast Calculation Functions ---

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return None

def relative_luminance(rgb):
    """Calculate relative luminance for WCAG contrast formula"""
    r, g, b = [x / 255.0 for x in rgb]
    
    # Apply gamma correction
    def adjust(color):
        if color <= 0.03928:
            return color / 12.92
        else:
            return ((color + 0.055) / 1.055) ** 2.4
    
    r = adjust(r)
    g = adjust(g)
    b = adjust(b)
    
    # Calculate luminance
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def contrast_ratio(color1_hex, color2_hex):
    """Calculate WCAG contrast ratio between two hex colors"""
    try:
        rgb1 = hex_to_rgb(color1_hex)
        rgb2 = hex_to_rgb(color2_hex)
        
        if not rgb1 or not rgb2:
            return None
        
        lum1 = relative_luminance(rgb1)
        lum2 = relative_luminance(rgb2)
        
        # Ensure lighter color is in numerator
        lighter = max(lum1, lum2)
        darker = min(lum1, lum2)
        
        ratio = (lighter + 0.05) / (darker + 0.05)
        return round(ratio, 2)
    except:
        return None

def parse_hex_colors(color_string):
    """Extract all hex color codes from a string"""
    if not color_string or str(color_string).lower() == 'nan':
        return []
    
    # Find all hex color codes
    hex_pattern = r'#[0-9a-fA-F]{6}'
    colors = re.findall(hex_pattern, str(color_string))
    return list(set(colors))  # Remove duplicates

def check_multi_color_contrast(colors):
    """Check contrast ratios between all color pairs"""
    results = []
    
    if len(colors) < 2:
        return results
    
    # Check all pairs
    for i in range(len(colors)):
        for j in range(i + 1, len(colors)):
            ratio = contrast_ratio(colors[i], colors[j])
            if ratio is not None:
                results.append({
                    'color1': colors[i],
                    'color2': colors[j],
                    'ratio': ratio,
                    'passes_3_1': ratio >= 3.0,
                    'passes_4_5_1': ratio >= 4.5
                })
    
    return results

# --- Helper functions for intelligent issue detection ---

def detect_color_issues(row):
    """Detect specific color accessibility issues"""
    issues = []
    
    # Check for red/green combinations (colorblind issue)
    colors = str(row.get('Colors Used (first 10)', '')).lower()
    color_notes = str(row.get('Color Notes', '')).lower()
    
    if ('red' in color_notes or '#ff' in colors or '#e6' in colors) and \
       ('green' in color_notes or '#00ff' in colors or '#38a8' in colors):
        issues.append("Red/green color combination detected - colorblind accessibility issue")
    
    # Check for light colors that may have contrast issues
    light_colors = ['#ffffff', '#ffff', '#ffffe0', '#f0f0f0']
    if any(lc in colors for lc in light_colors):
        issues.append("Light colors detected - verify contrast against background")
    
    # CRITICAL: Check if single color (cannot guarantee 3:1 contrast)
    uses_multiple = str(row.get('Uses Multiple Colors', '')).strip().lower()
    if uses_multiple in ['no', 'false', '0', '']:
        issues.append("Single color symbology - CANNOT GUARANTEE 3:1 contrast ratio (manual verification required)")
    
    # If multiple colors, check their contrast against each other
    if uses_multiple in ['yes', 'true', '1']:
        hex_colors = parse_hex_colors(row.get('Colors Used (first 10)', ''))
        if len(hex_colors) >= 2:
            contrast_results = check_multi_color_contrast(hex_colors)
            
            # Check if any pairs fail 3:1
            failing_pairs = [r for r in contrast_results if not r['passes_3_1']]
            if failing_pairs:
                for pair in failing_pairs:
                    issues.append(
                        "Colors {0} and {1} have {2}:1 contrast (FAILS 3:1 minimum for graphics)".format(
                            pair['color1'], pair['color2'], pair['ratio']
                        )
                    )
            else:
                # All pairs pass, but still note it
                min_ratio = min([r['ratio'] for r in contrast_results]) if contrast_results else 0
                issues.append("Multiple colors with minimum {0}:1 contrast (meets 3:1 for graphics)".format(min_ratio))
        else:
            issues.append("Multiple colors declared but hex codes not detected - verify distinguishability")
    
    return issues

def detect_contrast_issues(row):
    """Detect potential contrast problems"""
    issues = []
    contrast_text = str(row.get('Estimated Contrast Issues', '')).strip()
    
    if contrast_text and contrast_text.lower() not in ['nan', 'none', '']:
        issues.append(contrast_text)
    
    # Check transparency
    transparency = str(row.get('Transparency', '')).strip()
    if transparency and transparency not in ['', 'nan', '0', '100']:
        try:
            trans_val = float(transparency)
            if 0 < trans_val < 100:
                issues.append("Transparency set to {0}% - reduces contrast, must verify against background".format(trans_val))
        except:
            pass
    
    # Check if we can calculate contrast between multiple colors
    uses_multiple = str(row.get('Uses Multiple Colors', '')).strip().lower()
    hex_colors = parse_hex_colors(row.get('Colors Used (first 10)', ''))
    
    if uses_multiple in ['yes', 'true', '1'] and len(hex_colors) >= 2:
        contrast_results = check_multi_color_contrast(hex_colors)
        
        if contrast_results:
            issues.append("Multi-color contrast measured between symbols - still verify against map background")
    else:
        # Single color - always requires manual verification
        issues.append("Manual contrast measurement required against map background (WCAG 2.1 AA: 3:1 for graphics, 4.5:1 for text)")
    
    return issues

def detect_label_issues(row):
    """Detect label accessibility issues"""
    issues = []
    
    # Check if labels are enabled
    labels_enabled = str(row.get('Labels Enabled', '')).strip().lower()
    if labels_enabled not in ['yes', 'true', '1']:
        return []  # No labels, no label issues
    
    # Check halo
    halo_enabled = str(row.get('Halo Enabled', '')).strip().lower()
    if halo_enabled not in ['yes', 'true', '1']:
        issues.append("Labels lack halo - CRITICAL for contrast over varied backgrounds")
    else:
        # If halo exists, check contrast between label and halo
        font_color = str(row.get('Font Color', '')).strip()
        halo_color = str(row.get('Halo Color', '')).strip()
        
        if font_color and halo_color:
            ratio = contrast_ratio(font_color, halo_color)
            if ratio is not None:
                if ratio < 4.5:
                    issues.append("Label/halo contrast {0}:1 FAILS 4.5:1 minimum for text".format(ratio))
                else:
                    issues.append("Label/halo contrast {0}:1 meets 4.5:1 for text".format(ratio))
    
    # Check font size
    font_size = str(row.get('Font Size', '')).strip()
    if font_size and font_size not in ['', 'nan']:
        try:
            size = float(font_size)
            if size < 10:
                issues.append("Font size {0}pt is below 10pt minimum recommendation".format(size))
            elif size < 12:
                issues.append("Font size {0}pt is below 12pt recommended for better readability".format(size))
        except:
            pass
    
    # Check label issues column
    label_issue_text = str(row.get('Label Issues', '')).strip()
    if label_issue_text and label_issue_text.lower() not in ['', 'nan', 'false', 'no']:
        issues.append(label_issue_text)
    
    return issues

def detect_popup_issues(row):
    """Detect popup accessibility issues"""
    issues = []
    
    popup_enabled = str(row.get('Popup Enabled', '')).strip().lower()
    if popup_enabled in ['yes', 'true', '1']:
        # Check if popup fields exist
        popup_fields = str(row.get('Popup Fields (sample)', '')).strip()
        if not popup_fields or popup_fields == 'nan':
            issues.append("Popup enabled but no fields detected")
        
        # Flag for manual HTML review
        issues.append("Review popup HTML for: alt text on images, color contrast, semantic structure")
    elif popup_enabled in ['unknown', '']:
        issues.append("Popup configuration unknown - manual verification required")
    
    return issues

def generate_contrast_measurements(row):
    """Generate detailed contrast measurements for the audit"""
    measurements = []
    
    uses_multiple = str(row.get('Uses Multiple Colors', '')).strip().lower()
    hex_colors = parse_hex_colors(row.get('Colors Used (first 10)', ''))
    
    # Symbol color contrasts
    if uses_multiple in ['yes', 'true', '1'] and len(hex_colors) >= 2:
        contrast_results = check_multi_color_contrast(hex_colors)
        measurements.append("=== SYMBOL COLORS ===")
        for result in contrast_results:
            status = "PASS" if result['passes_3_1'] else "FAIL"
            measurements.append(
                "{0} vs {1}: {2}:1 [{3} 3:1]".format(
                    result['color1'], result['color2'], result['ratio'], status
                )
            )
    
    # Label/halo contrast
    labels_enabled = str(row.get('Labels Enabled', '')).strip().lower()
    if labels_enabled in ['yes', 'true', '1']:
        font_color = str(row.get('Font Color', '')).strip()
        halo_color = str(row.get('Halo Color', '')).strip()
        
        if font_color and halo_color:
            ratio = contrast_ratio(font_color, halo_color)
            if ratio is not None:
                status = "PASS" if ratio >= 4.5 else "FAIL"
                measurements.append("=== LABEL CONTRAST ===")
                measurements.append("Text vs Halo: {0}:1 [{1} 4.5:1]".format(ratio, status))
    
    return "\n".join(measurements) if measurements else ""

def determine_initial_status(color_issues, contrast_issues, label_issues, popup_issues):
    """Intelligently determine initial audit status"""
    # Check for critical issues
    critical_keywords = [
        'red/green', 'single color', 'lack halo', 'cannot guarantee',
        'fails 3:1', 'fails 4.5:1', 'fail 3:1', 'fail 4.5:1'
    ]
    has_critical = any(
        any(keyword in str(issue).lower() for keyword in critical_keywords)
        for issue in (color_issues + contrast_issues + label_issues + popup_issues)
    )
    
    # Check for passing contrast ratios
    passing_keywords = ['meets 3:1', 'meets 4.5:1', 'pass 3:1', 'pass 4.5:1']
    has_passing = any(
        any(keyword in str(issue).lower() for keyword in passing_keywords)
        for issue in (color_issues + contrast_issues + label_issues)
    )
    
    if has_critical:
        return "needs-work"
    elif has_passing and not has_critical:
        return "needs-work"
    else:
        return "needs-work"

def clean_text(text):
    """Clean text values from CSV"""
    text = str(text).strip()
    if text.lower() in ['nan', 'none', '']:
        return ''
    return text

# --- Load and combine CSVs ---
dfs = []
for f in csv_files:
    try:
        df_temp = pd.read_csv(f, quotechar='"', on_bad_lines='skip', encoding='utf-8')
        dfs.append(df_temp)
        print("Loaded: {0} ({1} rows)".format(f, len(df_temp)))
    except Exception as e:
        print("Error loading {0}: {1}".format(f, e))

df = pd.concat(dfs, ignore_index=True)
print("\nTotal combined rows: {0}".format(len(df)))

# --- Prepare JSON structure with intelligent analysis ---
baseline_data = {}
today = date.today().isoformat()

stats = {
    'total': 0,
    'pass': 0,
    'needs_work': 0,
    'with_color_issues': 0,
    'with_contrast_issues': 0,
    'with_label_issues': 0,
    'with_popup_issues': 0,
    'single_color_layers': 0,
    'critical_issues': 0,
    'contrast_calculated': 0,
    'contrast_passes': 0,
    'contrast_fails': 0
}

for _, row in df.iterrows():
    map_name = clean_text(row.get("Map Name", ""))
    layer_name = clean_text(row.get("Layer Name", ""))
    
    if not map_name or not layer_name:
        continue
    
    key = "{0}|||{1}".format(map_name, layer_name)
    stats['total'] += 1
    
    # Detect issues intelligently
    color_issue_list = detect_color_issues(row)
    contrast_issue_list = detect_contrast_issues(row)
    label_issue_list = detect_label_issues(row)
    popup_issue_list = detect_popup_issues(row)
    
    # Generate contrast measurements
    contrast_measurements = generate_contrast_measurements(row)
    if contrast_measurements:
        stats['contrast_calculated'] += 1
        if 'PASS' in contrast_measurements:
            stats['contrast_passes'] += 1
        if 'FAIL' in contrast_measurements:
            stats['contrast_fails'] += 1
    
    has_color_issues = len(color_issue_list) > 0
    has_contrast_issues = len(contrast_issue_list) > 0
    has_label_issues = len(label_issue_list) > 0
    has_popup_issues = len(popup_issue_list) > 0
    
    # Track specific critical issues
    uses_multiple = str(row.get('Uses Multiple Colors', '')).strip().lower()
    if uses_multiple in ['no', 'false', '0', '']:
        stats['single_color_layers'] += 1
    
    critical_keywords = ['red/green', 'single color', 'lack halo', 'cannot guarantee', 'fails']
    if any(
        any(keyword in str(issue).lower() for keyword in critical_keywords)
        for issue in (color_issue_list + contrast_issue_list + label_issue_list)
    ):
        stats['critical_issues'] += 1
    
    # Update stats
    if has_color_issues: stats['with_color_issues'] += 1
    if has_contrast_issues: stats['with_contrast_issues'] += 1
    if has_label_issues: stats['with_label_issues'] += 1
    if has_popup_issues: stats['with_popup_issues'] += 1
    
    # Determine initial status
    initial_status = determine_initial_status(
        color_issue_list, contrast_issue_list, 
        label_issue_list, popup_issue_list
    )
    
    if initial_status == 'pass': stats['pass'] += 1
    else: stats['needs_work'] += 1
    
    # Build comprehensive color notes
    color_notes_parts = []
    color_notes_parts.append("Symbology Type: {0}".format(clean_text(row.get('Symbology Type', ''))))
    color_notes_parts.append("Colors: {0}".format(clean_text(row.get('Colors Used (first 10)', ''))))
    color_notes_parts.append("Multiple Colors: {0}".format(clean_text(row.get('Uses Multiple Colors', ''))))
    
    line_widths = clean_text(row.get('Line Widths', ''))
    if line_widths:
        color_notes_parts.append("Line Widths: {0}".format(line_widths))
    
    transparency = clean_text(row.get('Transparency', ''))
    if transparency:
        color_notes_parts.append("Transparency: {0}".format(transparency))
    
    original_notes = clean_text(row.get('Color Notes', ''))
    if original_notes:
        color_notes_parts.append("Notes: {0}".format(original_notes))
    
    if color_issue_list:
        color_notes_parts.append("ISSUES: {0}".format('; '.join(color_issue_list)))
    
    # Build comprehensive label notes
    label_notes_parts = []
    labels_enabled = clean_text(row.get('Labels Enabled', ''))
    
    if labels_enabled in ['Yes', 'yes', 'True', 'true', '1']:
        label_notes_parts.append("Labels: ENABLED")
        label_notes_parts.append("Font: {0} {1}pt".format(
            clean_text(row.get('Font Name', '')), 
            clean_text(row.get('Font Size', ''))
        ))
        
        if clean_text(row.get('Font Bold', '')).lower() in ['yes', 'true', '1']:
            label_notes_parts.append("Bold: Yes")
        
        font_color = clean_text(row.get('Font Color', ''))
        if font_color:
            label_notes_parts.append("Color: {0}".format(font_color))
        
        halo = clean_text(row.get('Halo Enabled', ''))
        if halo.lower() in ['yes', 'true', '1']:
            halo_color = clean_text(row.get('Halo Color', ''))
            halo_size = clean_text(row.get('Halo Size', ''))
            label_notes_parts.append("Halo: {0} ({1})".format(halo_color, halo_size))
        else:
            label_notes_parts.append("Halo: NONE")
        
        if label_issue_list:
            label_notes_parts.append("ISSUES: {0}".format('; '.join(label_issue_list)))
    else:
        label_notes_parts.append("Labels: DISABLED")
    
    # Build contrast notes from detected issues
    contrast_notes = " | ".join(contrast_issue_list) if contrast_issue_list else ""
    
    # Build popup notes
    popup_notes_parts = []
    popup_enabled = clean_text(row.get('Popup Enabled', ''))
    popup_fields_count = clean_text(row.get('Popup Fields Count', ''))
    
    if popup_enabled.lower() in ['yes', 'true', '1']:
        popup_notes_parts.append("Enabled with {0} fields".format(popup_fields_count))
        popup_notes_parts.append("Fields: {0}".format(clean_text(row.get('Popup Fields (sample)', ''))))
    else:
        popup_notes_parts.append("Popup: Unknown/Not configured")
    
    if popup_issue_list:
        popup_notes_parts.append("ISSUES: {0}".format('; '.join(popup_issue_list)))
    
    # Build comprehensive issues summary
    issues_summary_parts = []
    if color_issue_list:
        issues_summary_parts.append("COLOR: {0}".format('; '.join(color_issue_list)))
    if contrast_issue_list:
        issues_summary_parts.append("CONTRAST: {0}".format('; '.join(contrast_issue_list)))
    if label_issue_list:
        issues_summary_parts.append("LABELS: {0}".format('; '.join(label_issue_list)))
    if popup_issue_list:
        issues_summary_parts.append("POPUPS: {0}".format('; '.join(popup_issue_list)))
    
    baseline_data[key] = {
        "status": initial_status,
        "auditDate": today,
        "auditor": "Tess Boada (Automated)",
        "colorIssues": has_color_issues,
        "colorNotes": " | ".join(color_notes_parts),
        "contrastIssues": has_contrast_issues,
        "contrastMeasurements": contrast_measurements,
        "contrastNotes": contrast_notes,
        "symbolIssues": False,
        "symbolNotes": "",
        "labelIssues": has_label_issues,
        "labelNotes": " | ".join(label_notes_parts),
        "popupIssues": has_popup_issues,
        "popupNotes": " | ".join(popup_notes_parts),
        "popupHeaderBg": "",
        "popupHeaderText": "",
        "popupRestrictedBg": "",
        "popupFontSize": "",
        "issuesSummary": " || ".join(issues_summary_parts)
    }

# --- Save to JSON ---
output_file = r"Y:\LayerAudit\Baseline_Audit_OSMP_All_Layers.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(baseline_data, f, indent=2)

# --- Print summary report ---
print("\nJSON file generated: {0}".format(output_file))
print("\n" + "="*70)
print("AUDIT BASELINE SUMMARY WITH AUTOMATED CONTRAST CHECKING")
print("="*70)
print("Total Layers:                    {0}".format(stats['total']))
print("Pass (No Issues):                {0} ({1:.1f}%)".format(stats['pass'], stats['pass']/stats['total']*100))
print("Needs Work:                      {0} ({1:.1f}%)".format(stats['needs_work'], stats['needs_work']/stats['total']*100))
print("\nAutomated Contrast Analysis:")
print("  Layers with calculated contrast: {0}".format(stats['contrast_calculated']))
print("  Passing 3:1 or 4.5:1:            {0}".format(stats['contrast_passes']))
print("  Failing contrast standards:      {0}".format(stats['contrast_fails']))
print("\nCritical Issues:")
print("  Single color layers:             {0}".format(stats['single_color_layers']))
print("  Total critical issues:           {0}".format(stats['critical_issues']))
print("\nIssue Breakdown:")
print("  Color Issues:                    {0}".format(stats['with_color_issues']))
print("  Contrast Issues:                 {0}".format(stats['with_contrast_issues']))
print("  Label Issues:                    {0}".format(stats['with_label_issues']))
print("  Popup Issues:                    {0}".format(stats['with_popup_issues']))
print("="*70)