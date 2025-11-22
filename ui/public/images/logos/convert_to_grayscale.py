import re
import colorsys

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb):
    """Convert RGB tuple to hex color"""
    return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))

def get_luminance(rgb):
    """Calculate relative luminance (0-1)"""
    r, g, b = [x / 255.0 for x in rgb]
    # Using relative luminance formula
    r = r / 12.92 if r <= 0.04045 else ((r + 0.055) / 1.055) ** 2.4
    g = g / 12.92 if g <= 0.04045 else ((g + 0.055) / 1.055) ** 2.4
    b = b / 12.92 if b <= 0.04045 else ((b + 0.055) / 1.055) ** 2.4
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def luminance_to_gray(luminance):
    """Map luminance to grayscale shades - more nuanced palette for better detail preservation"""
    # Create a richer palette with more shades to preserve detail
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

# Read the SVG file
with open('wan-logo.svg', 'r', encoding='utf-8') as f:
    content = f.read()

# Find all hex colors
color_pattern = r'fill="#([0-9A-Fa-f]{6})"'
colors = re.findall(color_pattern, content)

# Create mapping of original colors to grayscale
color_map = {}
for hex_color in set(colors):
    rgb = hex_to_rgb(hex_color)
    luminance = get_luminance(rgb)
    gray = luminance_to_gray(luminance)
    color_map[hex_color] = gray

# Replace all colors
for original, gray in color_map.items():
    content = content.replace(f'fill="#{original}"', f'fill="{gray}"')

# Write back
with open('wan-logo.svg', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Converted {len(color_map)} unique colors to grayscale")
print("Color mapping:")
for orig, gray in sorted(color_map.items()):
    print(f"  #{orig} -> {gray}")

