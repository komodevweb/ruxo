import re
import xml.etree.ElementTree as ET
import colorsys

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def get_luminance(rgb):
    """Calculate relative luminance (0-1)"""
    r, g, b = [x / 255.0 for x in rgb]
    # Using relative luminance formula
    r = r / 12.92 if r <= 0.04045 else ((r + 0.055) / 1.055) ** 2.4
    g = g / 12.92 if g <= 0.04045 else ((g + 0.055) / 1.055) ** 2.4
    b = b / 12.92 if b <= 0.04045 else ((b + 0.055) / 1.055) ** 2.4
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def luminance_to_gray(luminance):
    """Map luminance to grayscale shades - preserves detail with more shades"""
    # Rich palette with 10 shades for better detail preservation
    if luminance >= 0.95:
        return '#FFFFFF'  # White
    elif luminance >= 0.85:
        return '#F5F5F5'  # Very light grey
    elif luminance >= 0.75:
        return '#E5E5E5'  # Light grey
    elif luminance >= 0.65:
        return '#D0D0D0'  # Medium-light grey
    elif luminance >= 0.55:
        return '#B0B0B0'  # Medium grey
    elif luminance >= 0.45:
        return '#909090'  # Medium-dark grey
    elif luminance >= 0.35:
        return '#707070'  # Dark grey
    elif luminance >= 0.25:
        return '#505050'  # Darker grey
    elif luminance >= 0.15:
        return '#404040'  # Very dark grey
    else:
        return '#2A2A2A'  # Almost black

def get_shade_for_color(original_color):
    """Convert original color to grayscale based on luminance"""
    if original_color.upper() in ['NONE', 'TRANSPARENT']:
        return original_color
    
    # Handle hex colors
    if original_color.startswith('#'):
        rgb = hex_to_rgb(original_color)
        luminance = get_luminance(rgb)
        return luminance_to_gray(luminance)
    
    # If already a grayscale, return as is
    return original_color

def convert_svg_to_grayscale(filename):
    """Convert an SVG file to grayscale"""
    print(f"\n{'='*60}")
    print(f"Processing: {filename}")
    print(f"{'='*60}")
    
    # Read the SVG file
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all fill colors and convert them based on luminance
    color_pattern = r'fill="([^"]+)"'
    matches = list(re.finditer(color_pattern, content))
    
    # Create mapping of original colors to grayscale
    color_map = {}
    for match in matches:
        original_color = match.group(1)
        if original_color.upper() not in ['NONE', 'TRANSPARENT'] and original_color.startswith('#'):
            if original_color not in color_map:
                rgb = hex_to_rgb(original_color)
                luminance = get_luminance(rgb)
                gray = luminance_to_gray(luminance)
                color_map[original_color] = gray
    
    # Replace all colors
    for original, gray in color_map.items():
        content = content.replace(f'fill="{original}"', f'fill="{gray}"')
    
    # Write back
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Converted {len(color_map)} unique colors to grayscale")
    if color_map:
        print("Color mapping:")
        for orig, gray in sorted(color_map.items()):
            print(f"  {orig} -> {gray}")
    print("Using 10 grayscale shades for better detail preservation")

# Process multiple SVG files
files_to_process = [
    'icons8-google-logo-48.svg',
    'sora-color.svg',
    'kling-color.svg',
    'cropped-Seedance-1.0.svg',
    'cropped-Seedance.svg'
]

for filename in files_to_process:
    try:
        convert_svg_to_grayscale(filename)
    except FileNotFoundError:
        print(f"Warning: {filename} not found, skipping...")
    except Exception as e:
        print(f"Error processing {filename}: {e}")

print(f"\n{'='*60}")
print("Conversion complete!")
print(f"{'='*60}")

