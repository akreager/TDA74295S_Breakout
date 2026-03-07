#!/usr/bin/env python3
"""Convert Eagle .sch file to KiCad .kicad_sch format"""

import xml.etree.ElementTree as ET
import uuid
import math

def gen_uuid():
    return str(uuid.uuid4())

def mm(val_str):
    try:
        return float(val_str)
    except (ValueError, TypeError):
        return 0.0

# Eagle uses 0.1" grid; KiCad uses mm. Eagle sch coords are in inches * 25.4 = mm
# Actually Eagle XML coords are already in mm for newer versions
def eagle_rot_to_angle(rot_str):
    if not rot_str:
        return 0.0, False
    mirror = rot_str.startswith('M')
    angle_str = rot_str.lstrip('MSR')
    try:
        angle = float(angle_str)
    except ValueError:
        angle = 0.0
    return angle, mirror

def convert_sch(eagle_path, output_path):
    tree = ET.parse(eagle_path)
    root = tree.getroot()
    
    lines = []
    
    # Header
    lines.append('(kicad_sch (version 20230121) (generator eagle2kicad)')
    lines.append('')
    lines.append('  (uuid "' + gen_uuid() + '")')
    lines.append('')
    lines.append('  (paper "A")')
    lines.append('')
    
    # Collect all library symbols we'll need
    lib_symbols = []
    parts = root.findall('.//part')
    
    # Build a map of part -> library/deviceset/device
    part_map = {}
    for p in parts:
        part_map[p.get('name')] = {
            'library': p.get('library', ''),
            'deviceset': p.get('deviceset', ''),
            'device': p.get('device', ''),
            'value': p.get('value', ''),
        }
    
    # Get schematic sheet instances
    sheets = root.findall('.//sheet')
    
    # Write lib_symbols section
    lines.append('  (lib_symbols')
    
    # For each unique library symbol, create a KiCad symbol definition
    seen_symbols = set()
    
    for lib in root.findall('.//library'):
        lib_name = lib.get('name')
        for ds in lib.findall('.//deviceset'):
            ds_name = ds.get('name', '')
            
            # Get symbol(s) for this deviceset
            gates = ds.findall('.//gate')
            
            for device in ds.findall('.//device'):
                dev_name = device.get('name', '')
                full_name = f"{lib_name}:{ds_name}{dev_name}"
                
                if full_name in seen_symbols:
                    continue
                seen_symbols.add(full_name)
                
                # Get connections for pin mapping
                connections = {}
                for conn in device.findall('.//connect'):
                    gate_pin = f"{conn.get('gate')}.{conn.get('pin')}"
                    connections[gate_pin] = conn.get('pad', '')
                
                lines.append(f'    (symbol "{full_name}"')
                lines.append(f'      (in_bom yes) (on_board yes)')
                
                for gate in gates:
                    gate_name = gate.get('name', '')
                    sym_name = gate.get('symbol', '')
                    gx = mm(gate.get('x', '0'))
                    gy = mm(gate.get('y', '0'))
                    
                    # Find the symbol definition
                    sym = lib.find(f'.//symbol[@name="{sym_name}"]')
                    if sym is None:
                        continue
                    
                    unit_num = gates.index(gate) + 1
                    
                    # Sub-symbol units must NOT include library prefix
                    bare_name = f"{ds_name}{dev_name}"
                    lines.append(f'      (symbol "{bare_name}_{unit_num}_1"')
                    
                    # Symbol wires
                    for w in sym.findall('wire'):
                        layer = w.get('layer', '')
                        if layer != '94':  # 94 = Symbols layer
                            continue
                        x1 = mm(w.get('x1')) * 0.0254  # Eagle sch coords
                        y1 = mm(w.get('y1')) * 0.0254
                        x2 = mm(w.get('x2')) * 0.0254
                        y2 = mm(w.get('y2')) * 0.0254
                        # KiCad symbol coords are in mil (0.0254mm per mil)
                        lines.append(f'        (polyline (pts (xy {x1:.4f} {y1:.4f}) (xy {x2:.4f} {y2:.4f})) (stroke (width 0) (type default)) (fill (type none)))')
                    
                    # Symbol rectangles
                    for r in sym.findall('rectangle'):
                        layer = r.get('layer', '')
                        if layer != '94':
                            continue
                        rx1 = mm(r.get('x1')) * 0.0254
                        ry1 = mm(r.get('y1')) * 0.0254
                        rx2 = mm(r.get('x2')) * 0.0254
                        ry2 = mm(r.get('y2')) * 0.0254
                        lines.append(f'        (rectangle (start {rx1:.4f} {ry1:.4f}) (end {rx2:.4f} {ry2:.4f}) (stroke (width 0) (type default)) (fill (type background)))')
                    
                    # Symbol pins
                    for pin in sym.findall('pin'):
                        pin_name = pin.get('name', '')
                        px = mm(pin.get('x', '0')) * 0.0254
                        py = mm(pin.get('y', '0')) * 0.0254
                        length = mm(pin.get('length', 'middle'))
                        
                        # Length mapping
                        len_map = {'point': 0, 'short': 2.54, 'middle': 5.08, 'long': 7.62}
                        if isinstance(length, str):
                            pin_len = len_map.get(length, 5.08)
                        else:
                            pin_len = length * 0.0254
                        
                        rot = pin.get('rot', '')
                        angle, _ = eagle_rot_to_angle(rot)
                        
                        # Direction
                        visible = pin.get('visible', 'both')
                        direction = pin.get('direction', 'pas')
                        dir_map = {'in': 'input', 'out': 'output', 'io': 'bidirectional', 
                                   'pas': 'passive', 'pwr': 'power_in', 'sup': 'power_in',
                                   'hiz': 'tri_state', 'oc': 'open_collector', 'nc': 'no_connect'}
                        kicad_dir = dir_map.get(direction, 'passive')
                        
                        hide_name = 'hide' if visible == 'off' or visible == 'pad' else ''
                        hide_num = 'hide' if visible == 'off' or visible == 'pin' else ''
                        
                        # Get pad number from connections
                        pad_num = ''
                        gate_pin_key = f"{gate_name}.{pin_name}"
                        if gate_pin_key in connections:
                            pad_num = connections[gate_pin_key]
                        
                        lines.append(f'        (pin {kicad_dir} line (at {px:.4f} {py:.4f} {angle}) (length {pin_len:.4f}) (name "{pin_name}") (number "{pad_num}"))')
                    
                    lines.append(f'      )')  # end symbol unit
                
                lines.append(f'    )')  # end symbol
    
    lines.append('  )')  # end lib_symbols
    lines.append('')
    
    # Sheet content - instances, wires, junctions, labels, etc.
    if sheets:
        sheet = sheets[0]
        
        # Wires (nets)
        nets = sheet.findall('.//net')
        for net in nets:
            net_name = net.get('name', '')
            
            for seg in net.findall('segment'):
                # Wires in this segment
                for w in seg.findall('wire'):
                    x1, y1 = mm(w.get('x1')), -mm(w.get('y1'))
                    x2, y2 = mm(w.get('x2')), -mm(w.get('y2'))
                    lines.append(f'  (wire (pts (xy {x1:.4f} {y1:.4f}) (xy {x2:.4f} {y2:.4f})) (stroke (width 0) (type default)) (uuid "{gen_uuid()}"))')
                
                # Junctions
                for j in seg.findall('junction'):
                    jx, jy = mm(j.get('x')), -mm(j.get('y'))
                    lines.append(f'  (junction (at {jx:.4f} {jy:.4f}) (diameter 0) (color 0 0 0 0) (uuid "{gen_uuid()}"))')
                
                # Labels
                for lbl in seg.findall('label'):
                    lx, ly = mm(lbl.get('x')), -mm(lbl.get('y'))
                    rot = lbl.get('rot', '')
                    angle, _ = eagle_rot_to_angle(rot)
                    lines.append(f'  (label "{net_name}" (at {lx:.4f} {ly:.4f} {angle}) (effects (font (size 1.27 1.27))) (uuid "{gen_uuid()}"))')
        
        # Component instances
        instances = sheet.findall('.//instance')
        for inst in instances:
            part_name = inst.get('part', '')
            gate = inst.get('gate', '')
            x = mm(inst.get('x', '0'))
            y = -mm(inst.get('y', '0'))
            rot_str = inst.get('rot', '')
            angle, mirror = eagle_rot_to_angle(rot_str)
            
            if part_name not in part_map:
                continue
            
            pinfo = part_map[part_name]
            lib_name = pinfo['library']
            ds_name = pinfo['deviceset']
            dev_name = pinfo['device']
            value = pinfo['value']
            
            full_lib_name = f"{lib_name}:{ds_name}{dev_name}"
            
            mirror_str = ''
            if mirror:
                mirror_str = '(mirror x)'
            
            lines.append(f'  (symbol (lib_id "{full_lib_name}") (at {x:.4f} {y:.4f} {angle}) {mirror_str} (unit 1)')
            lines.append(f'    (in_bom yes) (on_board yes) (dnp no)')
            lines.append(f'    (uuid "{gen_uuid()}")')
            lines.append(f'    (property "Reference" "{part_name}" (at {x:.4f} {y-2:.4f} 0) (effects (font (size 1.27 1.27))))')
            lines.append(f'    (property "Value" "{value}" (at {x:.4f} {y+2:.4f} 0) (effects (font (size 1.27 1.27))))')
            lines.append(f'    (property "Footprint" "" (at {x:.4f} {y:.4f} 0) (effects (font (size 1.27 1.27)) hide))')
            lines.append(f'    (property "Datasheet" "" (at {x:.4f} {y:.4f} 0) (effects (font (size 1.27 1.27)) hide))')
            lines.append(f'  )')
            lines.append('')
    
    # Sheet instances
    lines.append('  (sheet_instances')
    lines.append(f'    (path "/" (page "1"))')
    lines.append('  )')
    lines.append('')
    
    lines.append(')')
    
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))
    
    return len(parts), len(root.findall('.//net'))

# Run
n_parts, n_nets = convert_sch('/mnt/project/TDA7429_BREAKOUT.sch', '/home/claude/TDA7429_BREAKOUT.kicad_sch')
print(f"Converted: {n_parts} parts, {n_nets} nets")
