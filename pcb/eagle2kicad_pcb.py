#!/usr/bin/env python3
"""Convert Eagle .brd file to KiCad .kicad_pcb format"""

import xml.etree.ElementTree as ET
import math
import uuid

def gen_uuid():
    return str(uuid.uuid4())

# Eagle layer to KiCad layer mapping
LAYER_MAP = {
    '1':  'F.Cu',
    '2':  'In1.Cu',
    '3':  'In2.Cu',
    '16': 'B.Cu',
    '17': 'F.Paste',
    '18': 'B.Paste',
    '19': 'F.Mask',  # actually stop mask (inverted in eagle)
    '20': 'Edge.Cuts',
    '21': 'F.SilkS',
    '22': 'B.SilkS',
    '25': 'F.SilkS',  # tNames
    '26': 'B.SilkS',  # bNames
    '27': 'F.SilkS',  # tValues
    '28': 'B.SilkS',  # bValues
    '29': 'F.Mask',    # tStop
    '30': 'B.Mask',    # bStop
    '31': 'F.Paste',   # tCream
    '32': 'B.Paste',   # bCream
    '35': 'F.Fab',     # tGlue  
    '36': 'B.Fab',     # bGlue
    '39': 'F.Fab',     # tKeepout
    '40': 'B.Fab',     # bKeepout
    '41': 'F.CrtYd',   # tRestrict
    '42': 'B.CrtYd',   # bRestrict
    '43': 'F.CrtYd',   # vRestrict
    '44': 'Edge.Cuts',
    '45': 'Cmts.User',
    '46': 'Cmts.User',
    '47': 'Cmts.User',
    '48': 'Cmts.User',
    '49': 'F.Fab',     # Reference
    '50': 'B.Fab',
    '51': 'F.SilkS',   # tDocu
    '52': 'B.SilkS',   # bDocu
}

def parse_eagle_brd(filepath):
    tree = ET.parse(filepath)
    return tree.getroot()

def eagle_rot_to_angle(rot_str):
    """Parse Eagle rotation string like 'R90', 'MR270', 'SR0' etc."""
    if not rot_str:
        return 0.0, False
    mirror = rot_str.startswith('M')
    angle_str = rot_str.lstrip('MSR')
    try:
        angle = float(angle_str)
    except ValueError:
        angle = 0.0
    return angle, mirror

def mm(val_str):
    """Convert Eagle coordinate string to float mm"""
    try:
        return float(val_str)
    except (ValueError, TypeError):
        return 0.0

def write_kicad_pcb(root, output_path):
    lines = []
    
    # Header
    lines.append('(kicad_pcb (version 20221018) (generator eagle2kicad)')
    lines.append('')
    lines.append('  (general')
    lines.append('    (thickness 1.6)')
    lines.append('  )')
    lines.append('')
    
    # Page setup
    lines.append('  (paper "A4")')
    lines.append('')
    
    # Layers
    lines.append('  (layers')
    lines.append('    (0 "F.Cu" signal)')
    lines.append('    (31 "B.Cu" signal)')
    lines.append('    (32 "B.Adhes" user "B.Adhesive")')
    lines.append('    (33 "F.Adhes" user "F.Adhesive")')
    lines.append('    (34 "B.Paste" user)')
    lines.append('    (35 "F.Paste" user)')
    lines.append('    (36 "B.SilkS" user "B.Silkscreen")')
    lines.append('    (37 "F.SilkS" user "F.Silkscreen")')
    lines.append('    (38 "B.Mask" user "B.Mask")')
    lines.append('    (39 "F.Mask" user "F.Mask")')
    lines.append('    (40 "Dwgs.User" user "User.Drawings")')
    lines.append('    (41 "Cmts.User" user "User.Comments")')
    lines.append('    (42 "Edge.Cuts" user)')
    lines.append('    (43 "Margin" user)')
    lines.append('    (44 "B.CrtYd" user "B.Courtyard")')
    lines.append('    (45 "F.CrtYd" user "F.Courtyard")')
    lines.append('    (46 "B.Fab" user "B.Fab")')
    lines.append('    (47 "F.Fab" user "F.Fab")')
    lines.append('  )')
    lines.append('')
    
    # Setup
    lines.append('  (setup')
    lines.append('    (pad_to_mask_clearance 0.1)')
    lines.append('    (pcbplotparams')
    lines.append('      (layerselection 0x00010fc_ffffffff)')
    lines.append('      (plotframeref false)')
    lines.append('      (viasonmask false)')
    lines.append('      (mode 1)')
    lines.append('      (useauxorigin false)')
    lines.append('      (hpglpennumber 1)')
    lines.append('      (hpglpenspeed 20)')
    lines.append('      (hpglpendiameter 15.000000)')
    lines.append('      (dxfpolygonmode true)')
    lines.append('      (dxfimperialunits true)')
    lines.append('      (dxfusepcbnewfont true)')
    lines.append('      (psnegative false)')
    lines.append('      (psa4output false)')
    lines.append('      (plotreference true)')
    lines.append('      (plotvalue true)')
    lines.append('      (plottextmode default)')
    lines.append('    )')
    lines.append('  )')
    lines.append('')
    
    # Nets
    signals = root.findall('.//signal')
    net_map = {'': 0}  # empty net = 0
    lines.append('  (net 0 "")')
    for i, sig in enumerate(signals, 1):
        name = sig.get('name', '')
        net_map[name] = i
        lines.append(f'  (net {i} "{name}")')
    lines.append('')
    
    # Board outline (Edge.Cuts) from dimension layer wires
    dim_wires = root.findall('.//wire[@layer="20"]')
    for w in dim_wires:
        x1, y1 = mm(w.get('x1')), -mm(w.get('y1'))
        x2, y2 = mm(w.get('x2')), -mm(w.get('y2'))
        width = mm(w.get('width', '0.15'))
        if width < 0.05:
            width = 0.15
        lines.append(f'  (gr_line (start {x1:.4f} {y1:.4f}) (end {x2:.4f} {y2:.4f}) (layer "Edge.Cuts") (width {width:.4f}) (tstamp {gen_uuid()}))')
    lines.append('')
    
    # Plain wires (non-signal traces on silkscreen, fab, etc.)
    plain = root.find('.//plain')
    if plain is not None:
        for w in plain.findall('wire'):
            layer = w.get('layer', '')
            kicad_layer = LAYER_MAP.get(layer)
            if kicad_layer and layer != '20':  # skip dimension (already handled)
                x1, y1 = mm(w.get('x1')), -mm(w.get('y1'))
                x2, y2 = mm(w.get('x2')), -mm(w.get('y2'))
                width = mm(w.get('width', '0.15'))
                if width < 0.01:
                    width = 0.15
                curve = mm(w.get('curve', '0'))
                if abs(curve) > 0.01:
                    # Arc - approximate as line for now
                    pass
                lines.append(f'  (gr_line (start {x1:.4f} {y1:.4f}) (end {x2:.4f} {y2:.4f}) (layer "{kicad_layer}") (width {width:.4f}) (tstamp {gen_uuid()}))')
        
        for t in plain.findall('text'):
            layer = t.get('layer', '')
            kicad_layer = LAYER_MAP.get(layer, 'F.SilkS')
            x, y = mm(t.get('x', '0')), -mm(t.get('y', '0'))
            size = mm(t.get('size', '1.27'))
            text_content = t.text or ''
            if text_content.strip():
                lines.append(f'  (gr_text "{text_content.strip()}" (at {x:.4f} {y:.4f}) (layer "{kicad_layer}") (effects (font (size {size:.4f} {size:.4f}) (thickness 0.15))) (tstamp {gen_uuid()}))')
    lines.append('')
    
    # Signal traces (copper wires)
    for sig in signals:
        name = sig.get('name', '')
        net_id = net_map.get(name, 0)
        
        for w in sig.findall('wire'):
            layer = w.get('layer', '')
            kicad_layer = LAYER_MAP.get(layer)
            if kicad_layer and 'Cu' in kicad_layer:
                x1, y1 = mm(w.get('x1')), -mm(w.get('y1'))
                x2, y2 = mm(w.get('x2')), -mm(w.get('y2'))
                width = mm(w.get('width', '0.25'))
                if width < 0.01:
                    width = 0.25
                lines.append(f'  (segment (start {x1:.4f} {y1:.4f}) (end {x2:.4f} {y2:.4f}) (width {width:.4f}) (layer "{kicad_layer}") (net {net_id}) (tstamp {gen_uuid()}))')
        
        # Vias
        for v in sig.findall('via'):
            x, y = mm(v.get('x')), -mm(v.get('y'))
            drill = mm(v.get('drill', '0.4'))
            size = drill + 0.5
            lines.append(f'  (via (at {x:.4f} {y:.4f}) (size {size:.4f}) (drill {drill:.4f}) (layers "F.Cu" "B.Cu") (net {net_id}) (tstamp {gen_uuid()}))')
        
        # Polygons (copper fills)
        for poly in sig.findall('polygon'):
            layer = poly.get('layer', '')
            kicad_layer = LAYER_MAP.get(layer)
            if kicad_layer and 'Cu' in kicad_layer:
                width = mm(poly.get('width', '0.25'))
                vertices = poly.findall('vertex')
                if len(vertices) >= 3:
                    lines.append(f'  (zone (net {net_id}) (net_name "{name}") (layer "{kicad_layer}") (tstamp {gen_uuid()})')
                    lines.append(f'    (connect_pads (clearance 0.3))')
                    lines.append(f'    (min_thickness 0.2)')
                    lines.append(f'    (fill yes (thermal_gap 0.508) (thermal_bridge_width 0.508))')
                    lines.append(f'    (polygon')
                    lines.append(f'      (pts')
                    for vtx in vertices:
                        vx, vy = mm(vtx.get('x')), -mm(vtx.get('y'))
                        lines.append(f'        (xy {vx:.4f} {vy:.4f})')
                    lines.append(f'      )')
                    lines.append(f'    )')
                    lines.append(f'  )')
    lines.append('')
    
    # Footprints (from elements)
    elements = root.findall('.//element')
    libraries = {}
    for lib in root.findall('.//library'):
        lib_name = lib.get('name')
        libraries[lib_name] = lib
    
    for elem in elements:
        elem_name = elem.get('name', '')
        pkg_name = elem.get('package', '')
        lib_name = elem.get('library', '')
        x = mm(elem.get('x', '0'))
        y = -mm(elem.get('y', '0'))
        rot_str = elem.get('rot', '')
        angle, mirror = eagle_rot_to_angle(rot_str)
        value = elem.get('value', '')
        
        # Find the package definition
        pkg = None
        if lib_name in libraries:
            for p in libraries[lib_name].findall(f'.//package[@name="{pkg_name}"]'):
                pkg = p
                break
        
        if pkg is None:
            # Try all libraries
            for lib in root.findall('.//packages/package'):
                if lib.get('name') == pkg_name:
                    pkg = lib
                    break
        
        layer = 'F.Cu'
        if mirror:
            layer = 'B.Cu'
        
        fp_uuid = gen_uuid()
        lines.append(f'  (footprint "{lib_name}:{pkg_name}" (layer "{layer}")')
        lines.append(f'    (tstamp {fp_uuid})')
        lines.append(f'    (at {x:.4f} {y:.4f} {angle})')
        
        # Reference and value
        lines.append(f'    (fp_text reference "{elem_name}" (at 0 -2) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))) (tstamp {gen_uuid()}))')
        lines.append(f'    (fp_text value "{value}" (at 0 2) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))) (tstamp {gen_uuid()}))')
        
        if pkg is not None:
            # Package wires (silkscreen, fab, etc.)
            for w in pkg.findall('wire'):
                wlayer = w.get('layer', '')
                kicad_wlayer = LAYER_MAP.get(wlayer)
                if kicad_wlayer:
                    wx1, wy1 = mm(w.get('x1')), -mm(w.get('y1'))
                    wx2, wy2 = mm(w.get('x2')), -mm(w.get('y2'))
                    wwidth = mm(w.get('width', '0.15'))
                    if wwidth < 0.01:
                        wwidth = 0.12
                    lines.append(f'    (fp_line (start {wx1:.4f} {wy1:.4f}) (end {wx2:.4f} {wy2:.4f}) (layer "{kicad_wlayer}") (width {wwidth:.4f}) (tstamp {gen_uuid()}))')
            
            # Package circles
            for c in pkg.findall('circle'):
                clayer = c.get('layer', '')
                kicad_clayer = LAYER_MAP.get(clayer)
                if kicad_clayer:
                    cx, cy = mm(c.get('x', '0')), -mm(c.get('y', '0'))
                    radius = mm(c.get('radius', '0.5'))
                    cwidth = mm(c.get('width', '0.15'))
                    if cwidth < 0.01:
                        cwidth = 0.12
                    lines.append(f'    (fp_circle (center {cx:.4f} {cy:.4f}) (end {cx+radius:.4f} {cy:.4f}) (layer "{kicad_clayer}") (width {cwidth:.4f}) (tstamp {gen_uuid()}))')
            
            # SMD pads
            for smd in pkg.findall('smd'):
                pad_name = smd.get('name', '')
                sx, sy = mm(smd.get('x', '0')), -mm(smd.get('y', '0'))
                sdx = mm(smd.get('dx', '1'))
                sdy = mm(smd.get('dy', '1'))
                smd_layer = smd.get('layer', '1')
                pad_layer = 'F.Cu' if smd_layer == '1' else 'B.Cu'
                roundness = mm(smd.get('roundness', '0'))
                
                # Determine pad shape
                shape = 'rect'
                if roundness > 50:
                    shape = 'roundrect'
                
                pad_rot = smd.get('rot', '')
                pad_angle, _ = eagle_rot_to_angle(pad_rot)
                
                at_str = f'{sx:.4f} {sy:.4f}'
                if pad_angle != 0:
                    at_str += f' {pad_angle}'
                
                # Find which net this pad connects to
                pad_net = 0
                pad_net_name = ''
                for sig in signals:
                    for cr in sig.findall(f'.//contactref[@element="{elem_name}"][@pad="{pad_name}"]'):
                        pad_net_name = sig.get('name', '')
                        pad_net = net_map.get(pad_net_name, 0)
                
                if pad_layer == 'F.Cu':
                    layers_str = '"F.Cu" "F.Paste" "F.Mask"'
                else:
                    layers_str = '"B.Cu" "B.Paste" "B.Mask"'
                
                lines.append(f'    (pad "{pad_name}" smd {shape} (at {at_str}) (size {sdx:.4f} {sdy:.4f}) (layers {layers_str}) (net {pad_net} "{pad_net_name}") (tstamp {gen_uuid()}))')
            
            # Through-hole pads
            for pad in pkg.findall('pad'):
                pad_name = pad.get('name', '')
                px, py = mm(pad.get('x', '0')), -mm(pad.get('y', '0'))
                drill = mm(pad.get('drill', '0.8'))
                diameter = mm(pad.get('diameter', '0'))
                if diameter == 0:
                    diameter = drill + 0.6
                
                pad_shape_eagle = pad.get('shape', 'round')
                if pad_shape_eagle == 'long':
                    shape = 'oval'
                    sx, sy = diameter * 1.5, diameter
                elif pad_shape_eagle == 'square':
                    shape = 'rect'
                    sx, sy = diameter, diameter
                elif pad_shape_eagle == 'octagon':
                    shape = 'roundrect'
                    sx, sy = diameter, diameter
                else:
                    shape = 'circle'
                    sx, sy = diameter, diameter
                
                pad_rot = pad.get('rot', '')
                pad_angle, _ = eagle_rot_to_angle(pad_rot)
                at_str = f'{px:.4f} {py:.4f}'
                if pad_angle != 0:
                    at_str += f' {pad_angle}'
                
                # Find net
                pad_net = 0
                pad_net_name = ''
                for sig in signals:
                    for cr in sig.findall(f'.//contactref[@element="{elem_name}"][@pad="{pad_name}"]'):
                        pad_net_name = sig.get('name', '')
                        pad_net = net_map.get(pad_net_name, 0)
                
                lines.append(f'    (pad "{pad_name}" thru_hole {shape} (at {at_str}) (size {sx:.4f} {sy:.4f}) (drill {drill:.4f}) (layers "*.Cu" "*.Mask") (net {pad_net} "{pad_net_name}") (tstamp {gen_uuid()}))')
        
        lines.append(f'  )')
        lines.append('')
    
    lines.append(')')
    
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))
    
    return len(elements), len(signals)

# Run conversion
root = parse_eagle_brd('/mnt/project/TDA7429_BREAKOUT.brd')
n_elem, n_sig = write_kicad_pcb(root, '/home/claude/TDA7429_BREAKOUT.kicad_pcb')
print(f"Converted: {n_elem} footprints, {n_sig} nets")
