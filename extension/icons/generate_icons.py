import os
import struct
import zlib
import math

def create_png(width, height, color_fn):
    raw_data = bytearray()
    for y in range(height):
        raw_data.append(0)  # filter type 0
        for x in range(width):
            r, g, b, a = color_fn(x, y, width, height)
            raw_data.extend([int(r), int(g), int(b), int(a)])
    
    compressed = zlib.compress(bytes(raw_data), 9)
    png = bytearray(b'\x89PNG\r\n\x1a\n')
    
    # IHDR
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    png.extend(struct.pack('>I', len(ihdr)) + b'IHDR' + ihdr + struct.pack('>I', zlib.crc32(b'IHDR' + ihdr) & 0xffffffff))
    
    # IDAT
    png.extend(struct.pack('>I', len(compressed)) + b'IDAT' + compressed + struct.pack('>I', zlib.crc32(b'IDAT' + compressed) & 0xffffffff))
    
    # IEND
    png.extend(struct.pack('>I', 0) + b'IEND' + struct.pack('>I', zlib.crc32(b'IEND') & 0xffffffff))
    return bytes(png)

def icon_color(x, y, width, height):
    # Normalized coordinates (-1 to 1)
    nx = (x / (width - 1)) * 2 - 1
    ny = (y / (height - 1)) * 2 - 1
    dist = math.sqrt(nx * nx + ny * ny)

    # Rounded rectangle mask
    corner_radius = 0.65
    ax = max(0, abs(nx) - (1 - corner_radius))
    ay = max(0, abs(ny) - (1 - corner_radius))
    corner_dist = math.sqrt(ax * ax + ay * ay)

    if corner_dist > corner_radius:
        return (0, 0, 0, 0)

    # Vibrant Gradient: Violet (#7c3aed) -> Crimson (#ef4444) -> Amber (#f59e0b)
    t = (x + y) / (width + height)
    r = int(124 + t * (239 - 124))
    g = int(58 + t * (68 - 58))
    b = int(237 + t * (68 - 237))

    # Inner symbol: Play triangle & Book lines
    # Center play triangle
    px = nx + 0.1
    py = ny
    # Triangle vertices: (-0.3, -0.35), (-0.3, 0.35), (0.35, 0)
    if px >= -0.25 and px <= 0.35:
        # Upper and lower bounds
        slope = 0.35 / 0.6
        if abs(py) <= (0.35 - (px - (-0.25)) * slope):
            # Symbol color: Pure white with soft glow
            return (255, 255, 255, 255)

    return (r, g, b, 255)

def main():
    icons_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(icons_dir, exist_ok=True)
    for size in [16, 48, 128]:
        png_data = create_png(size, size, icon_color)
        filepath = os.path.join(icons_dir, f"icon{size}.png")
        with open(filepath, "wb") as f:
            f.write(png_data)
        print(f"Generated {filepath} ({size}x{size})")

if __name__ == "__main__":
    main()
