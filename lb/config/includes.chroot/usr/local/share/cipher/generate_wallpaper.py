#!/usr/bin/env python3
"""CipherOS wallpaper generator — procedural cyberpunk hex-circuit background.

Used as the desktop wallpaper (hyprpaper), lock screen (hyprlock), and
SDDM login background. Builds a layered RGBA composite: numpy gradient
base -> hex grid -> circuit traces -> accent nodes -> hexagonal brand
glow ("Phantom Signal") -> vignette.
"""
import math
import random
from pathlib import Path

try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter
except ImportError:
    import subprocess
    subprocess.run(["pip3", "install", "--break-system-packages", "Pillow", "numpy"])
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter

W, H = 2560, 1440
OUTPUT = Path("/usr/local/share/cipher/assets/wallpaper-default.png")

CYAN = (0, 212, 255)
BLUE = (0, 128, 255)


def build_gradient() -> Image.Image:
    """Vectorized vertical + radial gradient — dark navy core brand colour."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    yy /= H
    xx /= W

    # Vertical gradient: near-black top, deep navy bottom
    base_r = 6 + yy * 10
    base_g = 6 + yy * 8
    base_b = 16 + yy * 26

    # Radial brightening toward center (subtle "glow from within")
    dx, dy = xx - 0.5, yy - 0.46
    dist = np.sqrt(dx * dx * 1.4 + dy * dy)
    radial = np.clip(1.0 - dist * 1.35, 0.0, 1.0) ** 2
    base_r += radial * 10
    base_g += radial * 22
    base_b += radial * 34

    arr = np.stack([base_r, base_g, base_b], axis=-1)
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, mode="RGB")


def draw_hex_grid(overlay: ImageDraw.ImageDraw, hex_size: int = 64) -> None:
    """Sparse hex-cell outlines — circuit-board substrate texture."""
    hex_w = hex_size * 1.5
    hex_h = hex_size * math.sqrt(3)
    rows = int(H / hex_h) + 3
    cols = int(W / hex_w) + 3
    for row in range(-2, rows):
        for col in range(-2, cols):
            cx = col * hex_w
            cy = row * hex_h + (hex_h / 2 if col % 2 else 0)
            if random.random() > 0.22:
                continue
            alpha = random.randint(20, 55)
            pts = [
                (cx + hex_size * math.cos(math.radians(60 * i - 30)),
                 cy + hex_size * math.sin(math.radians(60 * i - 30)))
                for i in range(6)
            ]
            overlay.polygon(pts, outline=(*CYAN, alpha))


def draw_circuit_traces(overlay: ImageDraw.ImageDraw, count: int = 110) -> None:
    """Right-angled neon traces with via-dots, like a PCB silkscreen."""
    for _ in range(count):
        x, y = random.randint(0, W), random.randint(0, H)
        alpha = random.randint(70, 170)
        width = random.choice([1, 1, 1, 2])
        color = (*CYAN, alpha) if random.random() < 0.7 else (*BLUE, alpha)
        direction = random.choice([(1, 0), (0, 1), (-1, 0), (0, -1)])
        segments = random.randint(2, 6)
        for _ in range(segments):
            seg_len = random.randint(50, 260)
            nx = max(0, min(W, x + direction[0] * seg_len))
            ny = max(0, min(H, y + direction[1] * seg_len))
            overlay.line([(x, y), (nx, ny)], fill=color, width=width)
            # Via dot at the bend
            if random.random() < 0.5:
                r = random.randint(2, 3)
                overlay.ellipse([nx - r, ny - r, nx + r, ny + r], fill=(*CYAN, min(255, alpha + 40)))
            x, y = nx, ny
            if random.random() < 0.55:
                direction = random.choice([(1, 0), (0, 1), (-1, 0), (0, -1)])


def draw_accent_nodes(glow_layer: ImageDraw.ImageDraw, count: int = 55) -> None:
    """Bright points that bloom after blur — the 'signal' in Phantom Signal."""
    for _ in range(count):
        x, y = random.randint(0, W), random.randint(0, H)
        r = random.randint(2, 5)
        glow_layer.ellipse([x - r, y - r, x + r, y + r], fill=(*CYAN, 255))


def draw_brand_glow(glow_layer: ImageDraw.ImageDraw) -> None:
    """Concentric hexagons radiating from center — the CipherOS ⬡ motif."""
    cx, cy = int(W * 0.5), int(H * 0.46)
    for i, size in enumerate(range(140, 760, 70)):
        alpha = max(0, 130 - i * 16)
        pts = [
            (cx + size * math.cos(math.radians(60 * k - 30)),
             cy + size * math.sin(math.radians(60 * k - 30)))
            for k in range(6)
        ]
        glow_layer.polygon(pts, outline=(*CYAN, alpha))
    # Solid bright core
    core_pts = [
        (cx + 30 * math.cos(math.radians(60 * k - 30)),
         cy + 30 * math.sin(math.radians(60 * k - 30)))
        for k in range(6)
    ]
    glow_layer.polygon(core_pts, fill=(*CYAN, 200))


def apply_vignette(img: Image.Image) -> Image.Image:
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dx, dy = xx / W - 0.5, yy / H - 0.5
    dist = np.sqrt(dx * dx + dy * dy)
    vig = np.clip(1.0 - (dist - 0.32) * 0.9, 0.45, 1.0)
    arr = np.array(img).astype(np.float32)
    arr *= vig[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def generate() -> None:
    random.seed(47)  # reproducible for build XLVII

    base = build_gradient().convert("RGBA")

    grid_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_hex_grid(ImageDraw.Draw(grid_layer))
    base = Image.alpha_composite(base, grid_layer)

    circuit_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_circuit_traces(ImageDraw.Draw(circuit_layer))
    base = Image.alpha_composite(base, circuit_layer)

    # Glow layer: nodes + brand hex, blurred for bloom, then additively screened
    glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    draw_accent_nodes(glow_draw)
    draw_brand_glow(glow_draw)
    glow_blurred = glow_layer.filter(ImageFilter.GaussianBlur(radius=6))

    base_rgb = np.array(base.convert("RGB")).astype(np.float32)
    glow_rgb = np.array(glow_blurred.convert("RGB")).astype(np.float32)
    glow_a = np.array(glow_blurred.split()[-1]).astype(np.float32) / 255.0
    screened = 255 - (255 - base_rgb) * (255 - glow_rgb * glow_a[..., None]) / 255
    combined = Image.fromarray(np.clip(screened, 0, 255).astype(np.uint8))

    # Sharp (unblurred) glow pass on top for crisp core highlights
    combined = Image.alpha_composite(combined.convert("RGBA"), glow_layer).convert("RGB")

    final = apply_vignette(combined)
    final = final.filter(ImageFilter.GaussianBlur(radius=0.4))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    final.save(str(OUTPUT), "PNG", optimize=True)
    print(f"Wallpaper saved: {OUTPUT} ({W}x{H})")


if __name__ == "__main__":
    generate()
