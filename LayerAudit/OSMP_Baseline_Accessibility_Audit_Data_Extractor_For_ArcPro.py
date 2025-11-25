"""
OSMP Baseline Accessibility Audit - Modernized Extractor
- Paste into ArcGIS Pro Python window or run standalone where arcpy is available.
- Produces CSV and a debug log on the user's desktop (detects OneDrive).
- Best-effort extraction of symbology (including CIM fallback), labels, popups,
  scale visibility, transparency, and line widths.

Notes:
- ArcGIS Pro exposes multiple symbology/representation models. This script
  attempts 'layer.symbology' first, then falls back to the CIM (layer.getDefinition("V2")).
- Some properties (especially popup HTML or complex CIM symbol internals) may
  require manual verification; the script flags unknowns and logs exceptions.
"""

import arcpy
import csv
import os
import logging
from datetime import datetime

# -----------------------------
# Helpers: paths & logging
# -----------------------------
def get_desktop_folder():
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, "Desktop"),
        os.path.join(home, "OneDrive", "Desktop"),
        os.path.join(home, "OneDrive - City of Boulder", "Desktop"),  # accomodate corporate OneDrive variations
        home
    ]
    for p in candidates:
        if os.path.isdir(p):
            return p
    return home

def setup_logging(map_name):
    desktop = get_desktop_folder()
    log_fname = f"OSMP_Audit_{map_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_path = os.path.join(desktop, log_fname)
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
    logging.info(f"Log started: {log_path}")
    return log_path

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
            return obj.get(attr, default)  # if it's dict-like
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
                logging.debug(f"layer.symbology parsing error for {layer.name}: {e}")

        # Fallback: try CIM - this often yields colors, opacities, widths
        if not info["colors"] or not info["line_widths"] or info["transparency"] == "":
            try:
                cim = layer.getDefinition("V2")
                # Opacity: CIM layer may have opacity (0..100)
                try:
                    opacity = safe_get(cim, "opacity")
                    if opacity is not None:
                        # CIM opacity is often 0..100
                        info["transparency"] = str(opacity)
                except Exception:
                    pass

                # Renderer + symbol
                cim_renderer = safe_get(cim, "renderer") or safe_get(cim, "Renderer")
                # sometimes renderer contains 'symbol' attribute
                if cim_renderer:
                    cim_symbol = safe_get(cim_renderer, "symbol")
                    # Many CIM symbols include nested symbol and symbolLayers arrays
                    def _extract_from_cim_symbol(sym):
                        try:
                            # symbolLayers may be an attribute or dict key
                            slayers = safe_get(sym, "symbolLayers") or []
                            for sl in slayers:
                                # color: some symbolLayers use 'color' -> { 'values': [r,g,b,a] }
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
                                # widths for stroke symbol layers
                                width = safe_get(sl, "width")
                                if width:
                                    info["line_widths"].append(str(width))
                                # some sl have 'opacity' 0..100
                                sl_op = safe_get(sl, "opacity")
                                if sl_op is not None and info["transparency"] == "":
                                    info["transparency"] = str(sl_op)
                        except Exception as ee:
                            logging.debug(f"Error extracting from cim symbol layers for {layer.name}: {ee}")

                    if cim_symbol:
                        _extract_from_cim_symbol(cim_symbol)
                    else:
                        # sometimes renderer contains 'groups' or 'classBreaks'
                        try:
                            groups = safe_get(cim_renderer, "groups") or safe_get(cim_renderer, "classBreaks") or []
                            for group in groups:
                                sym = safe_get(group, "symbol")
                                if sym:
                                    _extract_from_cim_symbol(sym)
                        except Exception:
                            pass
            except Exception as e:
                logging.debug(f"CIM fallback error for {layer.name}: {e}")

        # Final notes & checks
        if len(info["colors"]) >= 2:
            # simple red/green detection
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
        info["sym_notes"] = f"Error analyzing symbology: {e}"
        logging.exception(f"analyze_symbology failure for {layer.name}")

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
        "font_bold": False,
        "font_color": "",
        "halo_enabled": False,
        "halo_color": "",
        "halo_size": "",
        "label_notes": ""
    }
    try:
        # showLabels is common
        try:
            if hasattr(layer, "showLabels"):
                info["labels_enabled"] = bool(layer.showLabels)
        except Exception:
            pass

        # labelClasses in high-level API
        try:
            if hasattr(layer, "labelClasses") and len(layer.labelClasses) > 0:
                lc = layer.labelClasses[0]
                if hasattr(lc, "textSymbol"):
                    ts = lc.textSymbol
                    f = safe_get(ts, "font")
                    if f:
                        info["font_name"] = safe_get(f, "name") or info["font_name"]
                        size = safe_get(f, "size")
                        if size is not None:
                            info["font_size"] = str(size)
                        info["font_bold"] = bool(safe_get(f, "bold", False))
                    # color
                    col = safe_get(ts, "color")
                    if col and hasattr(col, "RGB"):
                        info["font_color"] = rgb_to_hex(col.RGB)
                    # halo
                    halo = safe_get(ts, "haloSymbol")
                    if halo:
                        info["halo_enabled"] = True
                        # halo color
                        if hasattr(halo, "color") and hasattr(halo.color, "RGB"):
                            info["halo_color"] = rgb_to_hex(halo.color.RGB)
                        # halo size
                        hs = safe_get(halo, "size")
                        if hs is not None:
                            info["halo_size"] = str(hs)
        except Exception as e:
            logging.debug(f"labelClasses parse error for {layer.name}: {e}")

        # Fallback to CIM for label font/color/halo
        if info["font_name"] == "" or info["font_size"] == "":
            try:
                cim = layer.getDefinition("V2")
                label_classes = safe_get(cim, "labelClasses") or []
                if label_classes:
                    lc = label_classes[0]
                    textsym = safe_get(lc, "textSymbol")
                    if textsym:
                        # font
                        font_obj = safe_get(textsym, "font") or {}
                        name = safe_get(font_obj, "name")
                        size = safe_get(font_obj, "size")
                        bold = safe_get(font_obj, "style")  # sometimes style encodes bold info - best-effort
                        if name:
                            info["font_name"] = name
                        if size:
                            info["font_size"] = str(size)
                        if isinstance(bold, bool):
                            info["font_bold"] = bold
                        # color: textSymbol.color.values
                        col = safe_get(textsym, "color")
                        if col and safe_get(col, "values"):
                            info["font_color"] = rgb_to_hex(col["values"] if isinstance(col, dict) else col.values)
                        # halo: textSymbol.haloSymbol
                        halo = safe_get(textsym, "haloSymbol")
                        if halo:
                            info["halo_enabled"] = True
                            hcol = safe_get(halo, "color")
                            if hcol and safe_get(hcol, "values"):
                                info["halo_color"] = rgb_to_hex(hcol["values"] if isinstance(hcol, dict) else hcol.values)
                            hs = safe_get(halo, "size")
                            if hs:
                                info["halo_size"] = str(hs)
            except Exception as e:
                logging.debug(f"CIM label fallback error for {layer.name}: {e}")

        # Simple accessibility check for font size
        try:
            if info["font_size"]:
                fnum = float(info["font_size"])
                if fnum < 10:
                    info["label_notes"] = "WARNING: Font size below 10pt may be too small"
        except Exception:
            pass

    except Exception as e:
        info["label_notes"] = f"Error analyzing labels: {e}"
        logging.exception(f"analyze_labels failed for {layer.name}")

    return info

def analyze_popups(layer):
    """
    Returns:
    {
      popup_enabled(bool or ''), popup_fields(list of names), popup_notes
    }
    """
    info = {
        "popup_enabled": "",
        "popup_fields": [],
        "popup_notes": ""
    }
    try:
        # high-level API: showPopups (bool)
        try:
            if hasattr(layer, "showPopups"):
                info["popup_enabled"] = bool(layer.showPopups)
        except Exception:
            pass

        # Try to list visible fields from layer.listFields() if available
        try:
            if hasattr(layer, "listFields"):
                fields = layer.listFields()
                visible_names = []
                for f in fields:
                    # arcpy Field objects do not have 'visible' — this is a best-effort filter:
                    #  - we include fields commonly used for popups, exclude shape FID etc.
                    if f.type.upper() not in ("OID", "OID64") and f.name.lower() not in ("shape", "shape_length", "shape_area"):
                        visible_names.append(f.name)
                info["popup_fields"] = visible_names
        except Exception as e:
            logging.debug(f"listFields issue for {layer.name}: {e}")

        # Try CIM popup info (popupInfo or popupInfo.display)
        try:
            cim = layer.getDefinition("V2")
            popup_info = safe_get(cim, "popupInfo") or safe_get(cim, "popupInfo", {})
            if popup_info:
                # If popupInfo contains 'fieldInfos'
                field_infos = safe_get(popup_info, "fieldInfos") or safe_get(popup_info, "fieldInfos", [])
                for fi in field_infos:
                    fld = safe_get(fi, "fieldName") or safe_get(fi, "field")
                    if fld and fld not in info["popup_fields"]:
                        info["popup_fields"].append(fld)
                # If popup has HTML content, flag for manual check
                has_html = False
                # try inspect content/description
                desc = safe_get(popup_info, "description") or safe_get(popup_info, "content")
                if desc:
                    has_html = True
                if has_html:
                    info["popup_notes"] = "Popup has HTML content - manually verify alt text and color/contrast"
        except Exception:
            # Not fatal; some layers don't expose popupInfo via CIM
            pass

        # If we couldn't determine anything:
        if info["popup_enabled"] == "" and not info["popup_fields"]:
            info["popup_notes"] = "Popup information not fully accessible programmatically - please verify in Map Properties"
    except Exception as e:
        info["popup_notes"] = f"Error analyzing popups: {e}"
        logging.exception(f"analyze_popups failed for {layer.name}")

    return info

def estimate_contrast_issues(sym_info, label_info, map_background_hex=""):
    """
    Basic heuristics:
    - flags labels without halo
    - flags light fill colors (very rough)
    Returns string of semicolon-separated issues
    """
    issues = []
    try:
        # label contrast
        if label_info.get("font_color") and not label_info.get("halo_enabled"):
            issues.append("Labels without halo - check contrast against varied backgrounds")

        # light colors
        light_colors = ['#ffffff', '#ffff00', '#00ffff', '#ffffe0']
        for c in sym_info.get("colors", []):
            if c.lower() in light_colors or any(c.lower().startswith(lc[:4]) for lc in light_colors):
                issues.append("Light symbology color detected - check contrast vs map background")
                break

        # transparency concerns
        trans = sym_info.get("transparency")
        if trans:
            try:
                tnum = float(trans)
                # assume opacity/opac value where >0 reduces contrast
                if tnum < 100:
                    issues.append("Symbol transparency detected - may reduce contrast")
            except Exception:
                pass

    except Exception as e:
        logging.debug(f"estimate_contrast_issues error: {e}")

    return "; ".join(issues) if issues else ""

# -----------------------------
# Main extraction
# -----------------------------
def extract_baseline_data():
    try:
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        current_map = aprx.activeMap
        if not current_map:
            print("ERROR: No active map found. Please open a map first.")
            return

        map_name = current_map.name
    except Exception as e:
        print("ERROR accessing project or map: ", e)
        return

    log_path = setup_logging(map_name)
    desktop = get_desktop_folder()
    csv_fname = f"OSMP_Baseline_{map_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    csv_path = os.path.join(desktop, csv_fname)

    headers = [
        "Map Name", "Layer Name", "Layer Type", "Data Source",
        "Symbology Type", "Colors Used (first 10)", "Uses Multiple Colors",
        "Color Notes", "Line Widths", "Transparency",
        "Estimated Contrast Issues",
        "Labels Enabled", "Font Name", "Font Size", "Font Bold", "Font Color",
        "Halo Enabled", "Halo Color", "Halo Size", "Label Issues",
        "Popup Enabled", "Popup Fields Count", "Popup Fields (sample)",
        "Min Scale", "Max Scale", "Extraction Notes"
    ]

    rows = []
    layer_count = 0

    logging.info(f"Starting extraction for map: {map_name}")
    for layer in current_map.listLayers():
        try:
            # Skip group or basemap layers if desired
            try:
                if getattr(layer, "isGroupLayer", False):
                    logging.info(f"Skipping group layer: {layer.name}")
                    continue
            except Exception:
                pass

            # Only consider feature or raster layers (skip tables, services w/out layers, etc.)
            if not (getattr(layer, "isFeatureLayer", False) or getattr(layer, "isRasterLayer", False)):
                logging.info(f"Skipping non-feature/non-raster layer: {layer.name} ({type(layer)})")
                continue

            layer_count += 1
            logging.info(f"Processing: {layer.name}")

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
                map_name,
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
            logging.info(f"  ✓ Extracted: colors={len(sym_info.get('colors', []))}; labels={label_info.get('labels_enabled')}")

        except Exception as e:
            logging.exception(f"ERROR processing layer: {getattr(layer, 'name', 'UNKNOWN')}")
            # Append an error row so you see which layer failed
            rows.append([
                map_name,
                getattr(layer, "name", "UNKNOWN"),
                "",
                "ERROR",
                "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", datetime.now().strftime("%Y-%m-%d"),
                f"Error during extraction: {e}"
            ])

    # Write CSV
    try:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
        logging.info(f"SUCCESS! Processed {layer_count} layers")
        logging.info(f"CSV saved to: {csv_path}")
        print("\n--- Extraction finished ---")
        print(f"Processed layers: {layer_count}")
        print(f"CSV: {csv_path}")
        print(f"Log: {log_path}")
        print("Note: Some items (complex CIM popups / HTML) may need manual review.")
    except Exception as e:
        logging.exception("ERROR writing CSV")
        print(f"ERROR writing CSV: {e}")
        print(f"Log: {log_path}")

# Run when executed directly in ArcGIS Pro Python window
if __name__ == "__main__":
    extract_baseline_data()
