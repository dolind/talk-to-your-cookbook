import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# Basic font
try:
    font = ImageFont.truetype("DejaVuSans.ttf", 32)
    font_bold = ImageFont.truetype("DejaVuSans-Bold.ttf", 38)
except:
    font = ImageFont.load_default()
    font_bold = font

# Text content (same as previous synthetic recipe)
data = [
    {
        "title": "Gebackener Hokkaido-Kürbis\nmit Kräuter-Joghurt & gerösteten Kernen",
        "subtitle": "FÜR 4 PERSONEN",
        "ingredients_title": "Zutaten",
        "ingredients": [
            "1 kleiner Hokkaido-Kürbis (ca. 1,2 kg), in Spalten",
            "2 rote Schalotten, halbiert",
            "3 EL Olivenöl",
            "1 TL Honig",
            "1 Knoblauchzehe, fein gehackt",
            "50 g Sonnenblumenkerne",
            "½ TL Paprikapulver, edelsüß",
            "Meersalz und frisch gemahlener Pfeffer",
        ],
        "instructions_title": "Zubereitung",
        "instructions": [
            "Den Ofen auf 220 °C vorheizen.",
            "Kürbisspalten und Schalotten in einer großen Schüssel mit Olivenöl, Honig,",
            "Knoblauch, Paprikapulver, Salz und Pfeffer mischen. Auf einem mit Backpapier",
            "belegten Blech verteilen und 25–35 Minuten im Ofen backen, bis der Kürbis weich",
            "ist und leicht gebräunt.",
            " ",
            "Währenddessen die Sonnenblumenkerne in einer kleinen Pfanne ohne Fett bei",
            "mittlerer Hitze 3–4 Minuten rösten, bis sie duften. Beiseitestellen.",
            " ",
            "Für den Kräuter-Joghurt Joghurt mit Petersilie, Schnittlauch, Zitronensaft,",
            "Zucker und etwas Salz glattrühren. Gegebenenfalls mit wenig Wasser",
            "cremiger machen.",
            " ",
            "Kürbis und Schalotten auf eine Platte geben, mit dem Joghurtdressing",
            "beträufeln und mit den gerösteten Kernen bestreuen. Sofort servieren.",
        ],
        "description": [
            "Ein einfaches Gericht mit intensiven Aromen. Der gebackene Kürbis erhält im Ofen ",
            "eine leichte Süße und eine zarte Textur, während der cremige Joghurt frische Kräuter ",
            "und eine feine Säure beisteuert. Die gerösteten Kerne sorgen für einen knackigen ",
            "Kontrast. Ideal als leichtes Hauptgericht oder als besondere Beilage.",
        ],
        "notes": [
            "Garzeit kann je nach Ofen variieren",
            "Mit frischen Kräutern servieren für mehr Aroma",
            "Eignet sich gut als vegetarische Hauptmahlzeit",
            "Reste können kalt im Salat verwendet werden",
            "Zu Reis oder Quinoa kombinieren",
        ],
    },
    {
        "title": "Hausgemachte Lasagne\nmit Tomaten-Ragù & Käsekruste",
        "subtitle": "FÜR 6 PERSONEN",
        "ingredients_title": "Zutaten",
        "ingredients": [
            "300 g Lasagneplatten (vorgegart oder frisch)",
            "400 g gemischtes Hackfleisch",
            "1 Zwiebel, fein gewürfelt",
            "1 Dose Tomaten (400 g)",
            "2 EL Tomatenmark",
            "200 g geriebener Käse",
            "300 ml Milch",
            "30 g Butter",
            "30 g Mehl",
            "1 EL Olivenöl",
            "Salz, Pfeffer",
            "Italienische Kräuter nach Geschmack",
        ],
        "instructions_title": "Zubereitung",
        "instructions": [
            "Olivenöl erhitzen und Zwiebel darin glasig dünsten.",
            "Hackfleisch zugeben und kräftig anbraten, anschließend Tomaten und Tomatenmark",
            "unterrühren. Mit Salz, Pfeffer und Kräutern würzen und ca. 15 Minuten köcheln lassen.",
            " ",
            "Für die Béchamelsauce Butter schmelzen, Mehl einrühren und kurz anschwitzen.",
            "Milch langsam unter Rühren zugeben, bis eine cremige Sauce entsteht.",
            " ",
            "Eine Auflaufform einfetten und abwechselnd Ragù, Lasagneplatten und Béchamel",
            "schichten. Mit Käse abschließen.",
            " ",
            "Im vorgeheizten Ofen bei 200 °C ca. 35–40 Minuten backen, bis die Oberfläche",
            "goldbraun ist.",
        ],
        "description": [
            "Ein klassisches Pastagericht, das mit saftigem Ragù und cremiger Béchamel ",
            "für herzhaften Genuss sorgt. Die Käsekruste bringt zusätzliche Würze und ",
            "macht die Lasagne zu einem Lieblingsrezept für die ganze Familie.",
        ],
        "notes": [
            "Für eine knusprige Kruste kurz unter den Grill stellen",
            "Lässt sich gut vorbereiten und aufwärmen",
            "Auch mit vegetarischem Hack möglich",
            "Reste eignen sich super fürs Meal Prepping",
        ],
    },
]


def wrap_text(text, font, max_width, draw):
    words = text.split(" ")
    lines = []
    current = []

    for w in words:
        current.append(w)
        # Measure width using textbbox
        bbox = draw.textbbox((0, 0), " ".join(current), font=font)
        width = bbox[2] - bbox[0]

        if width > max_width:
            current.pop()
            lines.append(" ".join(current))
            current = [w]

    if current:
        lines.append(" ".join(current))
    return lines


for idx, entry in enumerate(data):
    # Create a blank white page
    width, height = 1700, 2400
    img = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(img)
    x_margin = 120
    y = 120

    draw.text((x_margin, y), entry["subtitle"], font=font, fill=0)
    y += 80

    draw.text((x_margin, y), entry["title"], font=font_bold, fill=0)
    y += 100
    for line in entry["description"]:
        draw.text((x_margin, y), line, font=font, fill=0)
        y += 50
    y += 250
    y2 = y
    # Ingredients left column
    max_ing_width = 700
    for line in entry["ingredients"]:
        wrapped = wrap_text("• " + line, font, max_ing_width, draw)
        for w in wrapped:
            draw.text((x_margin, y), w, font=font, fill=0)
            y += 45

    # Instructions right column
    x2 = 950
    max_inst_width = 750

    for line in entry["instructions"]:
        wrapped = wrap_text(line, font, max_inst_width, draw)
        for w in wrapped:
            draw.text((x2, y2), w, font=font, fill=0)
            y2 += 45

    y2 += 100
    for line in entry["notes"]:
        draw.text((x_margin, y2), line, font=font, fill=0)
        y2 += 50

    np_img = np.array(img).astype(np.int16)
    noise = np.random.normal(0, 18, np_img.shape)
    np_img = np.clip(np_img + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(np_img)

    img = img.rotate(1.2, expand=True, fillcolor=255)
    img = img.filter(ImageFilter.GaussianBlur(0.7))

    # Display result
    img.save(f"text_{idx}.png")
