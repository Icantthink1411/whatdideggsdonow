from PIL import Image, ImageDraw, ImageFont
import json, os, textwrap

SITE_URL = "https://whatdideggsdonow.com"
OUT_DIR  = "/sessions/compassionate-sharp-newton/mnt/What did eggs do now/share"
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

# ── Fonts ──────────────────────────────────────────────────────
BOLD    = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REG     = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SERIF_B = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"

# ── Items (keep in sync with site data) ───────────────────────
items = [
  {"id":"eggs",     "name":"Eggs",          "unit":"1 dozen",       "emoji":"🥚","current":2.35,"previous":5.99,"yearAgo":3.29,"snark":"Down 61% from last week. The chickens had a moment of guilt and we are choosing to accept it."},
  {"id":"milk",     "name":"Milk",          "unit":"1 gallon",      "emoji":"🥛","current":4.07,"previous":3.89,"yearAgo":3.49,"snark":"Milk is up again, somehow, despite everything. The cows have observed what happened to the eggs."},
  {"id":"butter",   "name":"Butter",        "unit":"1 lb",          "emoji":"🧈","current":4.26,"previous":5.49,"yearAgo":4.19,"snark":"Butter is down 22% which sounds great until you remember it was outrageously expensive last week."},
  {"id":"bread",    "name":"Bread",         "unit":"1 loaf",        "emoji":"🍞","current":2.26,"previous":3.19,"yearAgo":2.79,"snark":"Bread is down 29% and honestly it's the only thing holding this grocery list together emotionally."},
  {"id":"beef",     "name":"Ground Beef",   "unit":"1 lb",          "emoji":"🥩","current":6.70,"previous":5.79,"yearAgo":4.89,"snark":"Ground beef is up 37% from last year and apparently has no intention of stopping."},
  {"id":"chicken",  "name":"Chicken Breast","unit":"1 lb",          "emoji":"🍗","current":4.17,"previous":4.29,"yearAgo":3.49,"snark":"Chicken breast is down slightly — the protein equivalent of a shrug."},
  {"id":"oliveoil", "name":"Olive Oil",     "unit":"16 oz bottle",  "emoji":"🫒","current":10.99,"previous":10.99,"yearAgo":8.99,"snark":"Olive oil has not moved a single cent, which is either reassuring or deeply suspicious."},
  {"id":"oj",       "name":"Orange Juice",  "unit":"64 oz",         "emoji":"🍊","current":6.49,"previous":6.49,"yearAgo":4.49,"snark":"Orange juice is up 44% from last year. Congratulations on your commitment to vitamin C."},
  {"id":"gas",      "name":"Regular Gas",   "unit":"1 gallon",      "emoji":"⛽","current":3.14,"previous":3.25,"yearAgo":3.45,"snark":"Down slightly. You're still paying to drive to the store to witness all the other prices on this list."},
  {"id":"diesel",   "name":"Diesel",        "unit":"1 gallon",      "emoji":"🚛","current":3.58,"previous":3.72,"yearAgo":3.89,"snark":"Diesel is down too. Everything you buy arrived on a truck, so enjoy this rare trickle-down moment."},
]

def pct(a, b):
    return (a - b) / b * 100

def trend(a, b):
    d = a - b
    return "flat" if abs(d) < 0.005 else ("up" if d > 0 else "down")

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
                            fill=color+"22", outline=color, width=2)
    draw.text((bx+12, by+8), badge_txt, font=tag_font, fill=color)

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
    t   = trend(item["current"], item["previous"])
    chg = pct(item["current"], item["previous"])
    sign = "+" if chg >= 0 else ""
    arrow = "UP" if t == "up" else ("DOWN" if t == "down" else "FLAT")
    title = f"{item['emoji']} {item['name']} — ${item['current']:.2f}/{item['unit']} this week"
    desc  = f"{arrow} {sign}{chg:.1f}% from last week. {item['snark']}"
    img_url = f"{SITE_URL}/share/og-{item['id']}.png"

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8" />
  <title>{title}</title>
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{desc}" />
  <meta property="og:image" content="{img_url}" />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
  <meta property="og:url" content="{SITE_URL}" />
  <meta property="og:type" content="website" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{title}" />
  <meta name="twitter:description" content="{desc}" />
  <meta name="twitter:image" content="{img_url}" />
  <meta http-equiv="refresh" content="0;url={SITE_URL}" />
  <script>window.location.href = "{SITE_URL}";</script>
</head>
<body><p>Redirecting... <a href="{SITE_URL}">Click here</a></p></body>
</html>"""
    path = os.path.join(OUT_DIR, f"{item['id']}.html")
    with open(path, "w") as f:
        f.write(html)
    return path

for item in items:
    img_path  = make_image(item)
    html_path = make_html(item)
    print(f"✓ {item['name']:20s}  →  {os.path.basename(img_path)}  +  {os.path.basename(html_path)}")

print(f"\nDone! {len(items)} items generated in {OUT_DIR}")
