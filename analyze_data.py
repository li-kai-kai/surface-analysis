import math

def parse_xyz(filepath):
    print(f"Reading {filepath}...")
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    # Parse header
    # Line 8 (index 7) seems to have the scale
    # 0 0.5 6.328e-007 0.5 1 0 0.00017452 1757694759
    if len(lines) < 15:
        print("File too short")
        return None, None

    header_line_8 = lines[7].split()
    try:
        scale = float(header_line_8[6])
    except:
        print("Could not parse scale from header line 8")
        scale = 0.00017452 # Fallback

    print(f"XYZ Scale from header: {scale}")

    min_ix, max_ix = float('inf'), float('-inf')
    min_iy, max_iy = float('inf'), float('-inf')
    
    count = 0
    for line in lines[14:]: # Data starts after header
        parts = line.strip().split()
        if len(parts) < 3:
            continue
        try:
            x_idx = int(parts[0])
            y_idx = int(parts[1])
            if parts[2] == "No":
                continue
            
            if x_idx < min_ix: min_ix = x_idx
            if x_idx > max_ix: max_ix = x_idx
            if y_idx < min_iy: min_iy = y_idx
            if y_idx > max_iy: max_iy = y_idx
            count += 1
        except ValueError:
            continue
            
    print(f"Parsed {count} valid points from XYZ")
    return (min_ix, max_ix, min_iy, max_iy), scale

def parse_txt(filepath):
    print(f"Reading {filepath}...")
    min_x, max_x = float('inf'), float('-inf')
    min_y, max_y = float('inf'), float('-inf')
    
    count = 0
    with open(filepath, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 3:
                try:
                    x = float(parts[0])
                    y = float(parts[1])
                    if x < min_x: min_x = x
                    if x > max_x: max_x = x
                    if y < min_y: min_y = y
                    if y > max_y: max_y = y
                    count += 1
                except ValueError:
                    continue
    print(f"Parsed {count} points from TXT")
    return (min_x, max_x, min_y, max_y)

def analyze():
    print("Parsing XYZ...")
    xyz_bounds, scale = parse_xyz('/Users/kaikai/Documents/projects/chip-process/005-avg.xyz')
    if not xyz_bounds:
        return

    print(f"XYZ bounds (indices):")
    print(f"X: {xyz_bounds[0]} to {xyz_bounds[1]}")
    print(f"Y: {xyz_bounds[2]} to {xyz_bounds[3]}")
    
    xyz_span_x = (xyz_bounds[1] - xyz_bounds[0]) * scale
    xyz_span_y = (xyz_bounds[3] - xyz_bounds[2]) * scale
    print(f"XYZ physical span (assuming scale {scale}): X={xyz_span_x:.4f}, Y={xyz_span_y:.4f}")

    print("\nParsing TXT...")
    txt_bounds = parse_txt('/Users/kaikai/Documents/projects/chip-process/005-avg.txt')
    print(f"TXT bounds:")
    print(f"X: {txt_bounds[0]} to {txt_bounds[1]}")
    print(f"Y: {txt_bounds[2]} to {txt_bounds[3]}")
    
    txt_span_x = txt_bounds[1] - txt_bounds[0]
    txt_span_y = txt_bounds[3] - txt_bounds[2]
    print(f"TXT physical span: X={txt_span_x:.4f}, Y={txt_span_y:.4f}")

    # Check center alignment
    xyz_center_x = (xyz_bounds[0] + xyz_bounds[1]) / 2 * scale
    xyz_center_y = (xyz_bounds[2] + xyz_bounds[3]) / 2 * scale
    
    txt_center_x = (txt_bounds[0] + txt_bounds[1]) / 2
    txt_center_y = (txt_bounds[2] + txt_bounds[3]) / 2
    
    print(f"\nCenters:")
    print(f"XYZ (scaled, raw): {xyz_center_x}, {xyz_center_y}")
    print(f"TXT: {txt_center_x}, {txt_center_y}")
    
    print(f"Offset X: {txt_center_x - xyz_center_x}")
    print(f"Offset Y: {txt_center_y - xyz_center_y}")

if __name__ == "__main__":
    analyze()
