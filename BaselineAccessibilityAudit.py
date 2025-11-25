"""
OSMP Baseline Accessibility Audit - Batch Layer File Processor
- Processes all .lyr and .lyrx files in a specified directory and subdirectories
- Produces a single combined CSV with all results
- Creates a detailed log file on the desktop
"""

import arcpy
import csv
import os
import logging
from datetime import datetime

# -----------------------------
# Configuration
# -----------------------------
LAYER_FILES_ROOT = r"E:\Layers"
OUTPUT_FOLDER = r"Y:\LayerAudit\Baseline Audits"

# -----------------------------
# Helpers: paths & logging
# -----------------------------
def get_desktop_folder():
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, "Desktop"),
        os.path.join(home, "OneDrive", "Desktop"),
        os.path.join(home, "OneDrive - City of Boulder", "Desktop"),
        home
    ]
    for p in candidates:
        if os.path.isdir(p):
            return p
    return home

def setup_logging():
    output_dir = OUTPUT_FOLDER if OUTPUT_FOLDER else get_desktop_folder()
    log_fname = "OSMP_Batch_Audit_{}.log".format(datetime.now().strftime('%Y%m%d_%H%M%S'))
    log_path = os.path.join(output_dir, log_fname)
    logging.basicConfig(
        filename=log_path,
        filemode='w',
        level=logging.DEBUG,
        format='%(asctime)s | %(levelname)s | %(message)s'
    )
    # also log to console
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(levelname)s | %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    logging.info("Log started: {}".format(log_path))
    return log_path

def find_layer_files(root_dir):
    """Recursively find all .lyr and .lyrx files, excluding _Archive paths"""
    layer_files = []
    skipped_archive_count = 0
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip any directory with _Archive in its path
        if "_Archive" in dirpath:
            skipped_archive_count += 1
            continue
            
        for filename in filenames:
            if filename.lower().endswith(('.lyr', '.lyrx')):
                full_path = os.path.join(dirpath, filename)
                layer_files.append(full_path)
    
    if skipped_archive_count > 0:
        logging.info("Skipped {} directories containing '_Archive' in path".format(skipped_archive_count))
    
    return layer_files

# -----------------------------
# Color and CIM helpers
# -----------------------------
def rgb_to_hex(rgb):
    """rgb: iterable of ints or floats (0-255 or 0-1) -> '#rrggbb'"""
    try:
        r, g, b = rgb[:3]
        # if floats 0..1, convert
        if 0.0 <= r <= 1.0 and 0.0 <= g <= 1.0 and 0.0 <= b <= 1.0:
            r, g, b = int(round(r * 255)), int(round(g * 255)), int(round(b * 255))
        else:
            r, g, b = int(round(r)), int(round(g)), int(round(b))
        return "#{:02x}{:02x}{:02x}".format(r, g, b)
    except Exception:
        return ""

def safe_get(obj, attr, default=None):
    try:
        return getattr(obj, attr)
    except Exception:
        try:
            return obj.get(attr, default)
        except Exception:
            return default

# -----------------------------
# Analyzer functions
# -----------------------------
def analyze_symbology(layer):
    """
    Returns dict:
    {
      symbol_type, colors (list hex), uses_multiple_colors (bool),
      color_notes, line_widths (list), transparency (0-100 or ''), sym_notes
    }
    """
    info = {
        "symbol_type": "",
        "colors": [],
        "uses_multiple_colors": False,
        "color_notes": "",
        "line_widths": [],
        "transparency": "",
        "sym_notes": ""
    }

    try:
        # Primary approach: layer.symbology (high-level API)
        if hasattr(layer, "symbology") and layer.symbology is not None:
            try:
                sym = layer.symbology
                renderer = safe_get(sym, "renderer")
                if renderer:
                    info["symbol_type"] = safe_get(renderer, "type") or info["symbol_type"]
                    # SimpleRenderer
                    if info["symbol_type"] == "SimpleRenderer":
                        sym_symbol = safe_get(renderer, "symbol")
                        if sym_symbol and hasattr(sym_symbol, "color"):
                            col = safe_get(sym_symbol.color, "RGB", None)
                            if col:
                                info["colors"].append(rgb_to_hex(col))
                        # Try stroke/width on symbol layers if present
                        try:
                            for sl in getattr(sym_symbol, "symbolLayers", []) or []:
                                width = safe_get(sl, "width")
                                if width:
                                    info["line_widths"].append(str(width))
                        except Exception:
                            pass

                    # UniqueValueRenderer / ClassBreaksRenderer
                    elif info["symbol_type"] in ("UniqueValueRenderer", "ClassBreaksRenderer"):
                        info["uses_multiple_colors"] = True
                        # iterate groups/items if available
                        try:
                            groups = safe_get(renderer, "groups") or []
                            for group in groups:
                                items = safe_get(group, "items") or []
                                for item in items:
                                    s = safe_get(item, "symbol")
                                    if s and hasattr(s, "color"):
                                        col = safe_get(s.color, "RGB", None)
                                        if col:
                                            hexc = rgb_to_hex(col)
                                            if hexc not in info["colors"]:
                                                info["colors"].append(hexc)
                                    # try symbolLayers for width
                                    try:
                                        for sl in getattr(s, "symbolLayers", []) or []:
                                            width = safe_get(sl, "width")
                                            if width:
                                                info["line_widths"].append(str(width))
                                    except Exception:
                                        pass
                        except Exception:
                            pass

            except Exception as e:
                logging.debug("layer.symbology parsing error for {}: {}".format(layer.name, e))

        # Fallback: try CIM - this often yields colors, opacities, widths
        if not info["colors"] or not info["line_widths"] or info["transparency"] == "":
            try:
                cim = layer.getDefinition("V2")
                # Opacity: CIM layer may have opacity (0..100)
                try:
                    opacity = safe_get(cim, "opacity")
                    if opacity is not None:
                        info["transparency"] = str(opacity)
                except Exception:
                    pass

                # Renderer + symbol
                cim_renderer = safe_get(cim, "renderer") or safe_get(cim, "Renderer")
                if cim_renderer:
                    cim_symbol = safe_get(cim_renderer, "symbol")
                    
                    def _extract_from_cim_symbol(sym):
                        try:
                            slayers = safe_get(sym, "symbolLayers") or []
                            for sl in slayers:
                                col = None
                                if hasattr(sl, "color"):
                                    col_attr = safe_get(sl, "color")
                                    if hasattr(col_attr, "values"):
                                        col = col_attr.values
                                elif isinstance(sl, dict) and "color" in sl and "values" in sl["color"]:
                                    col = sl["color"]["values"]
                                if col:
                                    hexc = rgb_to_hex(col)
                                    if hexc and hexc not in info["colors"]:
                                        info["colors"].append(hexc)
                                width = safe_get(sl, "width")
                                if width:
                                    info["line_widths"].append(str(width))
                                sl_op = safe_get(sl, "opacity")
                                if sl_op is not None and info["transparency"] == "":
                                    info["transparency"] = str(sl_op)
                        except Exception as ee:
                            logging.debug("Error extracting from cim symbol layers: {}".format(ee))

                    if cim_symbol:
                        _extract_from_cim_symbol(cim_symbol)
                    else:
                        try:
                            groups = safe_get(cim_renderer, "groups") or safe_get(cim_renderer, "classBreaks") or []
                            for group in groups:
                                sym = safe_get(group, "symbol")
                                if sym:
                                    _extract_from_cim_symbol(sym)
                        except Exception:
                            pass
            except Exception as e:
                logging.debug("CIM fallback error: {}".format(e))

        # Final notes & checks
        if len(info["colors"]) >= 2:
            try:
                has_red = any(c.lower().startswith("#ff") for c in info["colors"])
                has_green = any(c.lower()[1:3] == "00" and c.lower()[3:5] == "ff" for c in info["colors"])
                if has_red and has_green:
                    info["color_notes"] = "WARNING: Red/green combination detected (color blind issue)"
            except Exception:
                pass

        # dedupe line widths
        info["line_widths"] = sorted(set(info["line_widths"]), key=lambda x: float(x) if x.replace('.','',1).isdigit() else x)

    except Exception as e:
        info["sym_notes"] = "Error analyzing symbology: {}".format(e)
        logging.exception("analyze_symbology failure")

    return info

def analyze_labels(layer):
    """
    Returns dict:
    {
      labels_enabled, font_name, font_size, font_bold, font_color,
      halo_enabled, halo_color, halo_size, label_notes
    }
    """
    info = {
        "labels_enabled": False,
        "font_name": "",
        "font_size": "",
        "font_bold": "Unknown",  # Changed default to track if we found anything
        "font_color": "",
        "halo_enabled": "Unknown",  # Changed default to track if we found anything
        "halo_color": "",
        "halo_size": "",
        "label_notes": ""
    }
    try:
        # Check if labels are enabled
        try:
            if hasattr(layer, "showLabels"):
                info["labels_enabled"] = bool(layer.showLabels)
                logging.debug("  Layer {} - showLabels: {}".format(layer.name, layer.showLabels))
        except Exception as e:
            logging.debug("  Error checking showLabels: {}".format(e))

        # Try to get label class info via high-level API
        try:
            if hasattr(layer, "labelClasses") and len(layer.labelClasses) > 0:
                lc = layer.labelClasses[0]
                logging.debug("  Found labelClasses, count: {}".format(len(layer.labelClasses)))
                
                if hasattr(lc, "textSymbol"):
                    ts = lc.textSymbol
                    
                    # Font properties
                    f = safe_get(ts, "font")
                    if f:
                        info["font_name"] = safe_get(f, "name") or info["font_name"]
                        size = safe_get(f, "size")
                        if size is not None:
                            info["font_size"] = str(size)
                        
                        # Check bold - try multiple approaches
                        bold_val = safe_get(f, "bold")
                        if bold_val is not None:
                            info["font_bold"] = "Yes" if bool(bold_val) else "No"
                            logging.debug("  Font bold from high-level API: {}".format(bold_val))
                        
                        # Check weight property
                        weight_val = safe_get(f, "weight")
                        if weight_val is not None and info["font_bold"] == "Unknown":
                            info["font_bold"] = "Yes" if weight_val >= 600 else "No"
                            logging.debug("  Font bold from weight: {}".format(weight_val))
                        
                        style = safe_get(f, "style")
                        if style and "bold" in str(style).lower() and info["font_bold"] == "Unknown":
                            info["font_bold"] = "Yes"
                            logging.debug("  Font bold detected in style: {}".format(style))
                    
                    # Font color
                    col = safe_get(ts, "color")
                    if col and hasattr(col, "RGB"):
                        info["font_color"] = rgb_to_hex(col.RGB)
                    
                    # Halo - check multiple properties
                    halo = safe_get(ts, "haloSymbol")
                    if halo is not None:
                        info["halo_enabled"] = "Yes"
                        logging.debug("  Halo detected via high-level API haloSymbol")
                        if hasattr(halo, "color") and hasattr(halo.color, "RGB"):
                            info["halo_color"] = rgb_to_hex(halo.color.RGB)
                        hs = safe_get(halo, "size")
                        if hs is not None:
                            info["halo_size"] = str(hs)
                    else:
                        # Check if halo size exists even without haloSymbol object
                        halo_size = safe_get(ts, "haloSize")
                        if halo_size is not None and halo_size > 0:
                            info["halo_enabled"] = "Yes"
                            info["halo_size"] = str(halo_size)
                            logging.debug("  Halo detected via haloSize property: {}".format(halo_size))
                        elif info["halo_enabled"] == "Unknown":
                            info["halo_enabled"] = "No"
                            
        except Exception as e:
            logging.debug("  labelClasses parse error: {}".format(e))

        # CIM fallback - try to get more info
        if info["font_name"] == "" or info["font_size"] == "" or info["font_bold"] == "Unknown" or info["halo_enabled"] == "Unknown":
            try:
                cim = layer.getDefinition("V2")
                label_classes = safe_get(cim, "labelClasses") or []
                if label_classes:
                    lc = label_classes[0]
                    textsym = safe_get(lc, "textSymbol")
                    if textsym:
                        # Font
                        font_obj = safe_get(textsym, "font") or {}
                        name = safe_get(font_obj, "fontName") or safe_get(font_obj, "name") or safe_get(font_obj, "family")
                        size = safe_get(font_obj, "height") or safe_get(font_obj, "size")
                        
                        if name and not info["font_name"]:
                            info["font_name"] = name
                        if size and not info["font_size"]:
                            info["font_size"] = str(size)
                        
                        # Check for bold in CIM - multiple possible locations
                        if info["font_bold"] == "Unknown":
                            # Check weight
                            weight = safe_get(font_obj, "weight")
                            if weight is not None:
                                # Weight values: 400=normal, 700=bold
                                info["font_bold"] = "Yes" if weight >= 600 else "No"
                                logging.debug("  CIM font weight: {} -> bold={}".format(weight, info["font_bold"]))
                            else:
                                # Check bold property directly
                                bold_prop = safe_get(font_obj, "bold")
                                if bold_prop is not None:
                                    info["font_bold"] = "Yes" if bold_prop else "No"
                                    logging.debug("  CIM font bold property: {}".format(bold_prop))
                                else:
                                    # Check decoration or style
                                    decoration = safe_get(font_obj, "decoration")
                                    if decoration and "bold" in str(decoration).lower():
                                        info["font_bold"] = "Yes"
                                        logging.debug("  CIM font decoration indicates bold")
                                    else:
                                        # Still unknown - check font family name
                                        if name and any(x in name.lower() for x in ["bold", "heavy", "black"]):
                                            info["font_bold"] = "Yes"
                                            logging.debug("  Font name suggests bold: {}".format(name))
                                        else:
                                            info["font_bold"] = "No"  # Default to No if we've checked everything
                        
                        # Color
                        col = safe_get(textsym, "color")
                        if col and safe_get(col, "values") and not info["font_color"]:
                            info["font_color"] = rgb_to_hex(col["values"] if isinstance(col, dict) else col.values)
                        
                        # Halo - check CIM multiple ways
                        if info["halo_enabled"] == "Unknown":
                            halo = safe_get(textsym, "haloSymbol")
                            if halo:
                                info["halo_enabled"] = "Yes"
                                logging.debug("  Halo detected via CIM haloSymbol")
                                hcol = safe_get(halo, "color")
                                if hcol and safe_get(hcol, "values") and not info["halo_color"]:
                                    info["halo_color"] = rgb_to_hex(hcol["values"] if isinstance(hcol, dict) else hcol.values)
                                hs = safe_get(halo, "size") or safe_get(halo, "width")
                                if hs and not info["halo_size"]:
                                    info["halo_size"] = str(hs)
                            else:
                                # Check haloSize property directly
                                halo_size = safe_get(textsym, "haloSize")
                                if halo_size is not None and halo_size > 0:
                                    info["halo_enabled"] = "Yes"
                                    info["halo_size"] = str(halo_size)
                                    logging.debug("  CIM haloSize property: {}".format(halo_size))
                        
                        # Also check symbolLayers for halo
                        if info["halo_enabled"] == "Unknown":
                            sym_layers = safe_get(textsym, "symbolLayers") or []
                            for sl in sym_layers:
                                sl_type = safe_get(sl, "type") or ""
                                if "halo" in sl_type.lower():
                                    info["halo_enabled"] = "Yes"
                                    logging.debug("  Halo detected in CIM symbolLayers type: {}".format(sl_type))
                                    # Try to get halo size from symbol layer
                                    hs = safe_get(sl, "size") or safe_get(sl, "width")
                                    if hs and not info["halo_size"]:
                                        info["halo_size"] = str(hs)
                                    break
                            
                            # If still unknown after all checks
                            if info["halo_enabled"] == "Unknown":
                                info["halo_enabled"] = "No"
                                
            except Exception as e:
                logging.debug("  CIM label fallback error: {}".format(e))
        
        # Set final defaults if still unknown
        if info["font_bold"] == "Unknown":
            info["font_bold"] = "No"
        if info["halo_enabled"] == "Unknown":
            info["halo_enabled"] = "No"

        # Font size check
        try:
            if info["font_size"]:
                fnum = float(info["font_size"])
                if fnum < 10:
                    info["label_notes"] = "WARNING: Font size below 10pt may be too small"
        except Exception:
            pass

    except Exception as e:
        info["label_notes"] = "Error analyzing labels: {}".format(e)
        logging.exception("analyze_labels failed")

    return info

def analyze_popups(layer):
    """
    Returns:
    {
      popup_enabled(bool or ''), popup_fields(list of names), popup_notes
    }
    """
    info = {
        "popup_enabled": "Not stored in layer file",
        "popup_fields": [],
        "popup_notes": ""
    }
    
    notes = []
    
    try:
        # Try to get popup enabled status
        try:
            if hasattr(layer, "showPopups"):
                info["popup_enabled"] = "Yes" if bool(layer.showPopups) else "No"
                logging.debug("  showPopups property found: {}".format(layer.showPopups))
        except Exception as e:
            logging.debug("  showPopups not accessible: {}".format(e))

        # Get available fields from the layer
        field_count = 0
        visible_field_count = 0
        try:
            if hasattr(layer, "listFields"):
                fields = layer.listFields()
                field_count = len(fields)
                visible_names = []
                for f in fields:
                    # Count fields that would typically be shown in popups
                    if f.type.upper() not in ("OID", "OID64", "GEOMETRY", "BLOB", "RASTER") and \
                       f.name.lower() not in ("shape", "shape_length", "shape_area", "objectid", "fid"):
                        visible_names.append(f.name)
                        visible_field_count += 1
                info["popup_fields"] = visible_names
                
                if visible_field_count > 0:
                    notes.append("{} potential popup fields available".format(visible_field_count))
                else:
                    notes.append("No standard attribute fields found")
                    
        except Exception as e:
            logging.debug("  listFields issue: {}".format(e))
            notes.append("Could not access field list")

        # Try to extract CIM popup configuration
        has_popup_config = False
        try:
            cim = layer.getDefinition("V2")
            
            # Check for popupInfo in CIM
            popup_info = safe_get(cim, "popupInfo")
            if popup_info:
                has_popup_config = True
                
                # Check if popup is explicitly enabled/disabled
                enabled = safe_get(popup_info, "popupsEnabled")
                if enabled is not None:
                    info["popup_enabled"] = "Yes" if enabled else "No"
                
                # Get field configurations
                field_infos = safe_get(popup_info, "fieldInfos") or []
                visible_in_popup = []
                for fi in field_infos:
                    visible = safe_get(fi, "visible")
                    if visible is None or visible:  # Default to visible if not specified
                        fld = safe_get(fi, "fieldName") or safe_get(fi, "field")
                        if fld and fld not in visible_in_popup:
                            visible_in_popup.append(fld)
                
                if visible_in_popup:
                    info["popup_fields"] = visible_in_popup
                    notes.append("{} fields configured in popup".format(len(visible_in_popup)))
                
                # Check for custom HTML content
                desc = safe_get(popup_info, "description") or safe_get(popup_info, "content")
                if desc and len(str(desc).strip()) > 0:
                    notes.append("Custom HTML/text content detected")
                    if "<img" in str(desc).lower():
                        notes.append("WARNING: Images in popup - verify alt text")
                    if "color:" in str(desc).lower() or "style=" in str(desc).lower():
                        notes.append("WARNING: Custom styling - verify contrast")
                
                # Check popup title
                title = safe_get(popup_info, "title")
                if title:
                    notes.append("Has custom popup title")
                    
                # Check for media (charts, images, etc.)
                media = safe_get(popup_info, "mediaInfos") or []
                if media and len(media) > 0:
                    notes.append("WARNING: Contains {} media element(s) - verify accessibility".format(len(media)))
                    
        except Exception as e:
            logging.debug("  CIM popup analysis error: {}".format(e))

        # Final assessment
        if not has_popup_config and info["popup_enabled"] == "Not stored in layer file":
            notes.append("Popup config not found in layer file - check in map document")
        
        # Combine notes
        info["popup_notes"] = "; ".join(notes) if notes else "No popup configuration issues detected"

    except Exception as e:
        info["popup_notes"] = "Error analyzing popups: {}".format(e)
        logging.exception("analyze_popups failed")

    return info

def estimate_contrast_issues(sym_info, label_info):
    """
    Basic heuristics:
    - flags labels without halo
    - flags light fill colors (very rough)
    Returns string of semicolon-separated issues
    """
    issues = []
    try:
        if label_info.get("font_color") and not label_info.get("halo_enabled"):
            issues.append("Labels without halo - check contrast against varied backgrounds")

        light_colors = ['#ffffff', '#ffff00', '#00ffff', '#ffffe0']
        for c in sym_info.get("colors", []):
            if c.lower() in light_colors or any(c.lower().startswith(lc[:4]) for lc in light_colors):
                issues.append("Light symbology color detected - check contrast vs map background")
                break

        trans = sym_info.get("transparency")
        if trans:
            try:
                tnum = float(trans)
                if tnum < 100:
                    issues.append("Symbol transparency detected - may reduce contrast")
            except Exception:
                pass

    except Exception as e:
        logging.debug("estimate_contrast_issues error: {}".format(e))

    return "; ".join(issues) if issues else ""

# -----------------------------
# Process a single layer file
# -----------------------------
def process_layer_file(layer_file_path, relative_path):
    """Process a single .lyr or .lyrx file and return row data"""
    rows = []
    
    try:
        logging.info("Processing: {}".format(layer_file_path))
        
        # Load the layer file
        if layer_file_path.lower().endswith('.lyrx'):
            lyr = arcpy.mp.LayerFile(layer_file_path)
        else:
            # .lyr files (ArcMap format) - try to load
            lyr = arcpy.mp.LayerFile(layer_file_path)
        
        # Process each layer in the file (there may be multiple in a group)
        for layer in lyr.listLayers():
            try:
                # Skip group layers
                try:
                    if getattr(layer, "isGroupLayer", False):
                        logging.debug("Skipping group layer: {}".format(layer.name))
                        continue
                except Exception:
                    pass

                # Only process feature or raster layers
                if not (getattr(layer, "isFeatureLayer", False) or getattr(layer, "isRasterLayer", False)):
                    logging.debug("Skipping non-feature/non-raster layer: {}".format(layer.name))
                    continue

                logging.info("  Analyzing layer: {}".format(layer.name))

                # Data source
                data_source = ""
                try:
                    data_source = layer.dataSource if hasattr(layer, "dataSource") else ""
                except Exception:
                    data_source = ""

                # Symbology
                sym_info = analyze_symbology(layer)

                # Labels
                label_info = analyze_labels(layer)

                # Popups
                popup_info = analyze_popups(layer)

                # Scale visibility
                min_scale = ""
                max_scale = ""
                try:
                    min_scale = str(getattr(layer, "minScale", "")) or ""
                    max_scale = str(getattr(layer, "maxScale", "")) or ""
                except Exception:
                    pass

                # Estimate contrast issues
                contrast_issues = estimate_contrast_issues(sym_info, label_info)

                row = [
                    relative_path,
                    os.path.basename(layer_file_path),
                    layer.name,
                    "Feature" if getattr(layer, "isFeatureLayer", False) else "Raster" if getattr(layer, "isRasterLayer", False) else type(layer).__name__,
                    data_source,
                    sym_info.get("symbol_type", ""),
                    ", ".join(sym_info.get("colors", [])[:10]),
                    "Yes" if sym_info.get("uses_multiple_colors") else "No",
                    sym_info.get("color_notes", ""),
                    ", ".join(sym_info.get("line_widths", [])),
                    sym_info.get("transparency", ""),
                    contrast_issues,
                    "Yes" if label_info.get("labels_enabled") else "No",
                    label_info.get("font_name", ""),
                    label_info.get("font_size", ""),
                    "Yes" if label_info.get("font_bold") else "No",
                    label_info.get("font_color", ""),
                    "Yes" if label_info.get("halo_enabled") else "No",
                    label_info.get("halo_color", ""),
                    label_info.get("halo_size", ""),
                    label_info.get("label_notes", ""),
                    "Yes" if popup_info.get("popup_enabled") else ("Unknown" if popup_info.get("popup_enabled") == "" else "No"),
                    len(popup_info.get("popup_fields", [])),
                    ", ".join((popup_info.get("popup_fields") or [])[:10]),
                    min_scale,
                    max_scale,
                    "; ".join(filter(None, [sym_info.get("sym_notes", ""), popup_info.get("popup_notes", "")]))
                ]

                rows.append(row)
                logging.info("    Extracted: colors={}; labels={}; bold={}; halo={}".format(
                    len(sym_info.get('colors', [])), 
                    label_info.get('labels_enabled'),
                    label_info.get('font_bold'),
                    label_info.get('halo_enabled')
                ))

            except Exception as e:
                logging.exception("ERROR processing layer within file: {}".format(getattr(layer, 'name', 'UNKNOWN')))
                rows.append([
                    relative_path,
                    os.path.basename(layer_file_path),
                    getattr(layer, "name", "UNKNOWN"),
                    "",
                    "ERROR",
                    "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "",
                    "Error during extraction: {}".format(e)
                ])

    except Exception as e:
        logging.exception("ERROR processing layer file: {}".format(layer_file_path))
        rows.append([
            relative_path,
            os.path.basename(layer_file_path),
            "FILE_ERROR",
            "",
            "ERROR",
            "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "",
            "Error loading layer file: {}".format(e)
        ])

    return rows

# -----------------------------
# Main batch extraction
# -----------------------------
def extract_batch_baseline_data():
    log_path = setup_logging()
    
    logging.info("="*70)
    logging.info("OSMP BATCH LAYER FILE AUDIT")
    logging.info("="*70)
    logging.info("Root directory: {}".format(LAYER_FILES_ROOT))
    
    if not os.path.isdir(LAYER_FILES_ROOT):
        logging.error("ERROR: Root directory does not exist: {}".format(LAYER_FILES_ROOT))
        print("ERROR: Root directory does not exist: {}".format(LAYER_FILES_ROOT))
        return
    
    # Find all layer files
    logging.info("Searching for .lyr and .lyrx files...")
    layer_files = find_layer_files(LAYER_FILES_ROOT)
    logging.info("Found {} layer files".format(len(layer_files)))
    
    if len(layer_files) == 0:
        logging.warning("No layer files found in {}".format(LAYER_FILES_ROOT))
        print("No layer files found!")
        return
    
    # Prepare output
    output_dir = OUTPUT_FOLDER if OUTPUT_FOLDER else get_desktop_folder()
    csv_fname = "OSMP_Batch_Baseline_{}.csv".format(datetime.now().strftime('%Y%m%d_%H%M%S'))
    csv_path = os.path.join(output_dir, csv_fname)
    
    headers = [
        "Folder Path", "Layer File", "Layer Name", "Layer Type", "Data Source",
        "Symbology Type", "Colors Used (first 10)", "Uses Multiple Colors",
        "Color Notes", "Line Widths", "Transparency",
        "Estimated Contrast Issues",
        "Labels Enabled", "Font Name", "Font Size", "Font Bold", "Font Color",
        "Halo Enabled", "Halo Color", "Halo Size", "Label Issues",
        "Popup Enabled", "Popup Fields Count", "Popup Fields (sample)",
        "Min Scale", "Max Scale", "Extraction Notes"
    ]
    
    all_rows = []
    processed_count = 0
    error_count = 0
    
    # Process each layer file
    for layer_file in layer_files:
        # Get relative path for organization
        relative_path = os.path.relpath(os.path.dirname(layer_file), LAYER_FILES_ROOT)
        if relative_path == ".":
            relative_path = "Root"
        
        try:
            rows = process_layer_file(layer_file, relative_path)
            all_rows.extend(rows)
            processed_count += 1
            
            # Check for errors in rows
            if any("ERROR" in str(row) for row in rows):
                error_count += 1
                
        except Exception as e:
            logging.exception("Failed to process: {}".format(layer_file))
            error_count += 1
    
    # Write combined CSV
    try:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(all_rows)
        
        logging.info("="*70)
        logging.info("EXTRACTION COMPLETE")
        logging.info("="*70)
        logging.info("Processed {} layer files".format(processed_count))
        logging.info("Total layers extracted: {}".format(len(all_rows)))
        logging.info("Files with errors: {}".format(error_count))
        logging.info("CSV saved to: {}".format(csv_path))
        logging.info("Log saved to: {}".format(log_path))
        
        print("\n" + "="*70)
        print("BATCH EXTRACTION FINISHED")
        print("="*70)
        print("Processed layer files: {}".format(processed_count))
        print("Total layers extracted: {}".format(len(all_rows)))
        print("Files with errors: {}".format(error_count))
        print("CSV: {}".format(csv_path))
        print("Log: {}".format(log_path))
        print("\nNote: Review the log file for any errors or warnings.")
        
    except Exception as e:
        logging.exception("ERROR writing CSV")
        print("ERROR writing CSV: {}".format(e))
        print("Log: {}".format(log_path))

# -----------------------------
# Run
# -----------------------------
if __name__ == "__main__":
    extract_batch_baseline_data()
