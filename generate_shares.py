"""
Generate per-item share pages (share/<id>.html) and preview images
(share/og-<id>.png) from the current FALLBACK_ITEMS data in index.html.

Run after update_prices.py so social previews match the site:
    python generate_shares.py
"""
from PIL import Image, ImageDraw, ImageFont
import html as htmlmod, json, os, re, textwrap

SITE_URL = "https://whatdideggsdonow.com"
ROOT     = os.path.dirname(os.path.abspath(__file__))
OUT_DIR  = os.path.join(ROOT, "share")
os.makedirs(OUT_DIR, exist_ok=True)

# ── Colors ─────────────────────────────────────────────────────
BG      = "#FFFEF5"
YOLK    = "#F4C430"
YOLK_DK = "#D4A820"
DARK    = "#1A1A1A"
MID     = "#555555"
WHITE   = "#FFFFFF"
UP      = "#E53935"
DOWN    = "#2E7D32"
FLAT    = "#888888"

# ── Fonts (DejaVu on Linux/GitHub runner, Windows fallbacks) ──
def _font(*candidates):
    for c in candidates:
        if os.path.exists(c):
            return c
    raise FileNotFoundError(f"None of these fonts found: {candidates}")

_WIN = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
BOLD    = _font("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  os.path.join(_WIN, "arialbd.ttf"))
REG     = _font("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",       os.path.join(_WIN, "arial.ttf"))
SERIF_B = _font("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", os.path.join(_WIN, "georgiab.ttf"))

# ── Items: read from index.html so share pages always match the site ──
def load_items(html_path=os.path.join(ROOT, "index.html")):
    with open(html_path, encoding="utf-8") as f:
        page = f.read()
    block = re.search(r"const FALLBACK_ITEMS = (\[[\s\S]+?\]);", page).group(1)
    # Convert the JS object literal to JSON: quote bare keys (skipping text
    # inside string literals) and drop trailing commas.
    STR = r'"(?:\\.|[^"\\])*"'
    block = re.sub(STR + r'|([A-Za-z_]+)(?=\s*:)',
                   lambda m: f'"{m.group(1)}"' if m.group(1) else m.group(0), block)
    block = re.sub(STR + r'|,(\s*[\]}])',
                   lambda m: m.group(1) if m.group(1) is not None else m.group(0), block)
    return json.loads(block)

items = load_items()

def pct(a, b):
    return (a - b) / b * 100

def trend(a, b):
    d = a - b
    return "flat" if abs(d) < 0.005 else ("up" if d > 0 else "down")

def tint(hex_color, amount=0.13):
    """Light tint of hex_color over the background (RGB images ignore alpha)."""
    c  = [int(hex_color[i:i+2], 16) for i in (1, 3, 5)]
    bg = [int(BG[i:i+2], 16) for i in (1, 3, 5)]
    return tuple(round(b + (x - b) * amount) for x, b in zip(c, bg))

def make_image(item):
    W, H = 1200, 630
    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    t     = trend(item["current"], item["previous"])
    chg   = pct(item["current"], item["previous"])
    color = UP if t == "up" else (DOWN if t == "down" else FLAT)
    arrow = "UP" if t == "up" else ("DOWN" if t == "down" else "FLAT")
    sign  = "+" if chg >= 0 else ""

    # Background accent circles
    draw.ellipse([880, -100, 1280, 300], fill=YOLK)
    draw.ellipse([960, -30,  1200, 210], fill="#FAD84A")
    draw.ellipse([-60, 400, 180, 660],   fill=YOLK)

    # Item name (large)
    name_font  = ImageFont.truetype(SERIF_B, 88)
    sub_font   = ImageFont.truetype(BOLD, 34)
    price_font = ImageFont.truetype(BOLD, 72)
    tag_font   = ImageFont.truetype(BOLD, 38)
    tiny_font  = ImageFont.truetype(REG,  26)

    name = item["name"]
    draw.text((100, 80), name, font=name_font, fill=DARK)

    # Unit
    draw.text((100, 185), item["unit"], font=sub_font, fill=MID)

    # Divider
    draw.rectangle([100, 230, 560, 234], fill=YOLK_DK)

    # Price
    price_str = f"${item['current']:.2f}"
    draw.text((100, 255), price_str, font=price_font, fill=DARK)

    # Change badge
    badge_txt = f"{arrow} {sign}{chg:.1f}% this week"
    bbox = draw.textbbox((0,0), badge_txt, font=tag_font)
    bw = bbox[2]-bbox[0]+24
    bh = bbox[3]-bbox[1]+16
    bx, by = 100, 348
    draw.rounded_rectangle([bx, by, bx+bw, by+bh], radius=10,
                            fill=tint(color), outline=color, width=2)
    draw.text((bx+12-bbox[0], by+8-bbox[1]), badge_txt, font=tag_font, fill=color)

    # Snark text (wrapped)
    snark = item["snark"]
    lines = textwrap.wrap(snark, width=58)
    y = 430
    for line in lines[:2]:
        draw.text((100, y), line, font=tiny_font, fill=MID)
        y += 34

    # Site URL watermark
    draw.text((100, 585), "whatdideggsdonow.com", font=tiny_font, fill="#BBBBBB")

    path = os.path.join(OUT_DIR, f"og-{item['id']}.png")
    img.save(path, "PNG", optimize=True)
    return path

def make_html(item):
    t     = trend(item["current"], item["previous"])
    chg   = pct(item["current"], item["previous"])
    yoy   = pct(item["current"], item["yearAgo"])
    sign  = "+" if chg >= 0 else ""
    ysign = "+" if yoy >= 0 else ""
    arrow = {"up": "UP ↑", "down": "DOWN ↓", "flat": "FLAT →"}[t]
    color = UP if t == "up" else (DOWN if t == "down" else FLAT)
    badge_bg = "#%02X%02X%02X" % tint(color)
    e = htmlmod.escape
    title = f"{item['emoji']} {item['name']} — ${item['current']:.2f}/{item['unit']} this week"
    desc  = f"{arrow} {sign}{chg:.1f}% from last week. {item['snark']}"
    # Version the image URL so social sites re-fetch it when prices change
    ver      = f"{item['current']}-{item['previous']}".replace(".", "")
    img_url  = f"{SITE_URL}/share/og-{item['id']}.png?v={ver}"
    page_url = f"{SITE_URL}/share/{item['id']}"
    favicon  = "data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🥚</text></svg>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{e(title)} | What Did Eggs Do Now?</title>
  <meta name="description" content="{e(desc)}" />
  <meta property="og:title" content="{e(title)}" />
  <meta property="og:description" content="{e(desc)}" />
  <meta property="og:image" content="{img_url}" />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
  <meta property="og:url" content="{page_url}" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="What Did Eggs Do Now?" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{e(title)}" />
  <meta name="twitter:description" content="{e(desc)}" />
  <meta name="twitter:image" content="{img_url}" />
  <link rel="icon" href="{favicon}" />
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{background:#FFFEF5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:24px}}
    .card{{background:#fff;border-radius:20px;box-shadow:0 4px 24px rgba(0,0,0,0.09);max-width:480px;width:100%;overflow:hidden}}
    .card-header{{background:#F4C430;padding:20px 28px;text-align:center}}
    .site-name{{font-size:14px;font-weight:700;color:#1A1A1A;letter-spacing:0.5px}}
    .card-body{{padding:28px}}
    .item-name{{font-size:32px;font-weight:800;color:#1A1A1A;margin-bottom:4px}}
    .item-unit{{font-size:14px;color:#999;margin-bottom:20px}}
    .price-row{{display:flex;align-items:center;gap:12px;margin-bottom:16px}}
    .price{{font-size:48px;font-weight:800;color:#1A1A1A;line-height:1}}
    .badge{{font-size:14px;font-weight:700;padding:6px 12px;border-radius:20px;background:{badge_bg};color:{color}}}
    .yoy{{font-size:13px;color:#999;margin-bottom:16px}}
    .snark{{font-size:15px;color:#555;line-height:1.6;font-style:italic;border-left:3px solid {color};padding-left:14px;margin-bottom:24px}}
    .cta{{display:block;background:#F4C430;color:#1A1A1A;text-decoration:none;text-align:center;padding:14px 24px;border-radius:50px;font-weight:700;font-size:16px}}
    .cta:hover{{background:#D4A820}}
    .footer{{margin-top:16px;font-size:12px;color:#AAAAAA;text-align:center}}
  </style>
</head>
<body>
  <div class="card">
    <div class="card-header">
      <div class="site-name">🥚 What Did Eggs Do Now? — Weekly Price Tracker</div>
    </div>
    <div class="card-body">
      <div class="item-name">{item['emoji']} {e(item['name'])}</div>
      <div class="item-unit">{e(item['unit'])}</div>
      <div class="price-row">
        <span class="price">${item['current']:.2f}</span>
        <span class="badge">{arrow} {abs(chg):.1f}%</span>
      </div>
      <div class="yoy">vs. a year ago: ${item['yearAgo']:.2f} &nbsp;({ysign}{yoy:.1f}% year-over-year)</div>
      <div class="snark">{e(item['snark'])}</div>
      <a href="{SITE_URL}" class="cta">See All {len(items)} Prices This Week →</a>
    </div>
  </div>
  <div class="footer">National average · Sourced from FRED, BLS &amp; EIA data</div>
</body>
</html>
"""
    path = os.path.join(OUT_DIR, f"{item['id']}.html")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    return path

for item in items:
    img_path  = make_image(item)
    html_path = make_html(item)
    print(f"✓ {item['name']:20s}  →  {os.path.basename(img_path)}  +  {os.path.basename(html_path)}")

print(f"\nDone! {len(items)} items generated in {OUT_DIR}")
