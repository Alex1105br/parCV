import io
import re

from src.services.parser import extrair_texto_curriculo
from src.utils import escape_xml


def _parse_curriculo(texto):
    blocks = []
    lines = texto.strip().split("\n")
    header_idx = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue

        m = re.match(r"^---SECAO:\s*(.+?)\s*---$", line)
        if m:
            blocks.append({"type": "secao", "text": m.group(1).upper()})
            header_idx = 99
            continue

        m = re.match(r"^---EMPRESA:\s*(.+?)\s*---$", line)
        if m:
            blocks.append({"type": "empresa", "text": m.group(1)})
            continue

        m = re.match(r"^---CARGO:\s*(.+?)\s*---$", line)
        if m:
            blocks.append({"type": "cargo", "text": m.group(1)})
            continue

        if line.startswith("•") or line.startswith("-"):
            blocks.append({"type": "bullet", "text": line.lstrip("•- ").strip()})
            continue

        if header_idx == 0:
            blocks.append({"type": "nome", "text": line})
            header_idx = 1
            continue
        if header_idx == 1:
            if "@" in line or "linkedin" in line.lower() or "github" in line.lower() or "tel" in line.lower():
                blocks.append({"type": "contato", "text": line})
                header_idx = 99
            else:
                blocks.append({"type": "titulo", "text": line})
                header_idx = 2
            continue
        if header_idx == 2:
            blocks.append({"type": "contato", "text": line})
            header_idx = 99
            continue

        upper = line.upper()
        section_names = [
            "COMPETÊNCIAS", "COMPETENCIAS", "EXPERIÊNCIAS", "EXPERIENCIAS",
            "FORMAÇÃO", "FORMACAO", "PROJETOS", "IDIOMAS", "COMPETÊNCIAS-CHAVE",
            "COMPETENCIAS-CHAVE", "EDUCAÇÃO", "EDUCACAO", "HABILIDADES",
        ]
        if any(upper.startswith(s) for s in section_names) and len(line) < 50:
            blocks.append({"type": "secao", "text": upper})
            continue

        if "|" in line and any(c.isdigit() for c in line):
            blocks.append({"type": "empresa", "text": line})
            continue

        blocks.append({"type": "texto", "text": line})

    return blocks


def _find_font_dir():
    import os
    candidates = [
        "/usr/share/fonts/liberation-sans-fonts/",
        "/usr/share/fonts/truetype/liberation/",
        "/usr/share/fonts/TTF/",
        "/usr/share/fonts/truetype/",
    ]
    for d in candidates:
        if os.path.isfile(os.path.join(d, "LiberationSans-Regular.ttf")):
            return d
    import subprocess
    try:
        result = subprocess.run(
            ["fc-match", "-f", "%{file}", "Liberation Sans"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout:
            return os.path.dirname(result.stdout) + "/"
    except Exception:
        pass
    return candidates[0]


def _register_fonts(FONT_DIR):
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    try:
        pdfmetrics.registerFont(TTFont("Sans", FONT_DIR + "LiberationSans-Regular.ttf"))
        pdfmetrics.registerFont(TTFont("Sans-Bold", FONT_DIR + "LiberationSans-Bold.ttf"))
        pdfmetrics.registerFont(TTFont("Sans-Italic", FONT_DIR + "LiberationSans-Italic.ttf"))
    except Exception:
        pass


def _make_doc(buffer):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate
    return SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
    )


# ── Template: Clássico ────────────────────────────────────────────────────────

def _build_classico(blocks):
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import ParagraphStyle

    PRETO = colors.HexColor("#1a1a1a")
    CINZA = colors.HexColor("#555555")
    LINHA = colors.HexColor("#cccccc")
    AZUL  = colors.HexColor("#2c5282")

    def S(name, **kw):
        d = dict(fontName="Sans", textColor=PRETO, spaceAfter=2, spaceBefore=0, leading=14)
        d.update(kw)
        return ParagraphStyle(name, **d)

    styles = {
        "nome":    S("nome",    fontName="Sans-Bold",   fontSize=18, spaceAfter=2),
        "titulo":  S("titulo",  fontName="Sans-Italic", fontSize=10, spaceAfter=1, textColor=AZUL),
        "contato": S("contato", fontName="Sans",        fontSize=8.5, spaceAfter=8, textColor=CINZA),
        "secao":   S("secao",   fontName="Sans-Bold",   fontSize=9, spaceAfter=4, spaceBefore=14, textColor=AZUL),
        "empresa": S("empresa", fontName="Sans-Bold",   fontSize=9.5, spaceAfter=1, spaceBefore=8),
        "cargo":   S("cargo",   fontName="Sans-Italic", fontSize=9, spaceAfter=3, textColor=CINZA),
        "bullet":  S("bullet",  fontName="Sans",        fontSize=9, spaceAfter=2, leftIndent=10, leading=13),
        "texto":   S("texto",   fontName="Sans",        fontSize=9, spaceAfter=3, leading=13),
    }

    story = []
    for block in blocks:
        btype, text = block["type"], block["text"]
        if btype == "nome":
            story.append(Paragraph(text, styles["nome"]))
        elif btype == "titulo":
            story.append(Paragraph(text, styles["titulo"]))
        elif btype == "contato":
            story.append(Paragraph(text, styles["contato"]))
            story.append(HRFlowable(width="100%", thickness=1, color=PRETO, spaceAfter=6))
        elif btype == "secao":
            story.append(Paragraph(text, styles["secao"]))
            story.append(HRFlowable(width="100%", thickness=0.4, color=LINHA, spaceAfter=4))
        elif btype == "empresa":
            story.append(Spacer(1, 2))
            story.append(Paragraph(text, styles["empresa"]))
        elif btype == "cargo":
            story.append(Paragraph(text, styles["cargo"]))
        elif btype == "bullet":
            story.append(Paragraph(f"•  {text}", styles["bullet"]))
        else:
            story.append(Paragraph(text, styles["texto"]))
    return story


# ── Template: Moderno ─────────────────────────────────────────────────────────

def _build_moderno(blocks):
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import ParagraphStyle

    TEAL     = colors.HexColor("#0d7377")
    TEAL_LT  = colors.HexColor("#e8f7f7")
    PRETO    = colors.HexColor("#1a1a1a")
    CINZA    = colors.HexColor("#555555")
    BRANCO   = colors.HexColor("#ffffff")

    def S(name, **kw):
        d = dict(fontName="Sans", textColor=PRETO, spaceAfter=2, spaceBefore=0, leading=14)
        d.update(kw)
        return ParagraphStyle(name, **d)

    styles = {
        "nome":    S("nome-m",    fontName="Sans-Bold",   fontSize=20, spaceAfter=1, textColor=TEAL),
        "titulo":  S("titulo-m",  fontName="Sans-Italic", fontSize=10, spaceAfter=1, textColor=CINZA),
        "contato": S("contato-m", fontName="Sans",        fontSize=8.5, spaceAfter=10, textColor=CINZA),
        "secao":   S("secao-m",   fontName="Sans-Bold",   fontSize=8.5, spaceAfter=0, spaceBefore=0, textColor=BRANCO),
        "empresa": S("empresa-m", fontName="Sans-Bold",   fontSize=9.5, spaceAfter=1, spaceBefore=8),
        "cargo":   S("cargo-m",   fontName="Sans-Italic", fontSize=9, spaceAfter=3, textColor=CINZA),
        "bullet":  S("bullet-m",  fontName="Sans",        fontSize=9, spaceAfter=2, leftIndent=10, leading=13),
        "texto":   S("texto-m",   fontName="Sans",        fontSize=9, spaceAfter=3, leading=13),
    }

    PAGE_WIDTH = 21 * cm - 3.6 * cm  # A4 minus margins

    story = []
    for block in blocks:
        btype, text = block["type"], block["text"]
        if btype == "nome":
            story.append(Paragraph(text, styles["nome"]))
        elif btype == "titulo":
            story.append(Paragraph(text, styles["titulo"]))
        elif btype == "contato":
            story.append(Paragraph(text, styles["contato"]))
        elif btype == "secao":
            p = Paragraph(f"  {text}", styles["secao"])
            tbl = Table([[p]], colWidths=[PAGE_WIDTH], rowHeights=[16])
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), TEAL),
                ("TOPPADDING",    (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ]))
            story.append(Spacer(1, 10))
            story.append(tbl)
            story.append(Spacer(1, 4))
        elif btype == "empresa":
            story.append(Spacer(1, 2))
            story.append(Paragraph(text, styles["empresa"]))
        elif btype == "cargo":
            story.append(Paragraph(text, styles["cargo"]))
        elif btype == "bullet":
            story.append(Paragraph(f"•  {text}", styles["bullet"]))
        else:
            story.append(Paragraph(text, styles["texto"]))
    return story


# ── Template: Executivo ───────────────────────────────────────────────────────

def _build_executivo(blocks):
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import ParagraphStyle

    BURG     = colors.HexColor("#6b2737")
    BURG_LT  = colors.HexColor("#f7eaed")
    CINZA_ESC= colors.HexColor("#2d2d2d")
    CINZA    = colors.HexColor("#666666")
    LINHA    = colors.HexColor("#dddddd")

    def S(name, **kw):
        d = dict(fontName="Sans", textColor=CINZA_ESC, spaceAfter=2, spaceBefore=0, leading=14)
        d.update(kw)
        return ParagraphStyle(name, **d)

    styles = {
        "nome":    S("nome-e",    fontName="Sans-Bold",   fontSize=19, spaceAfter=2, textColor=CINZA_ESC),
        "titulo":  S("titulo-e",  fontName="Sans-Italic", fontSize=10, spaceAfter=1, textColor=BURG),
        "contato": S("contato-e", fontName="Sans",        fontSize=8.5, spaceAfter=8, textColor=CINZA),
        "secao":   S("secao-e",   fontName="Sans-Bold",   fontSize=9, spaceAfter=0, spaceBefore=0, textColor=BURG),
        "empresa": S("empresa-e", fontName="Sans-Bold",   fontSize=9.5, spaceAfter=1, spaceBefore=8),
        "cargo":   S("cargo-e",   fontName="Sans-Italic", fontSize=9, spaceAfter=3, textColor=CINZA),
        "bullet":  S("bullet-e",  fontName="Sans",        fontSize=9, spaceAfter=2, leftIndent=14, leading=13),
        "texto":   S("texto-e",   fontName="Sans",        fontSize=9, spaceAfter=3, leading=13),
    }

    PAGE_WIDTH = 21 * cm - 3.6 * cm

    story = []
    for block in blocks:
        btype, text = block["type"], block["text"]
        if btype == "nome":
            story.append(Paragraph(text, styles["nome"]))
        elif btype == "titulo":
            story.append(Paragraph(text, styles["titulo"]))
        elif btype == "contato":
            story.append(Paragraph(text, styles["contato"]))
            story.append(HRFlowable(width="100%", thickness=1.5, color=BURG, spaceAfter=6))
        elif btype == "secao":
            story.append(Spacer(1, 10))
            # Left accent bar via 2-column table
            accent = Table([[" ", Paragraph(text, styles["secao"])]], colWidths=[5, PAGE_WIDTH - 5])
            accent.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (0, 0), BURG),
                ("TOPPADDING",    (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING",   (0, 0), (-1, -1), 0),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
                ("LEFTPADDING",   (1, 0), (1, 0), 6),
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ]))
            story.append(accent)
            story.append(HRFlowable(width="100%", thickness=0.4, color=LINHA, spaceAfter=4))
        elif btype == "empresa":
            story.append(Spacer(1, 2))
            story.append(Paragraph(text, styles["empresa"]))
        elif btype == "cargo":
            story.append(Paragraph(text, styles["cargo"]))
        elif btype == "bullet":
            story.append(Paragraph(f"▸  {text}", styles["bullet"]))
        else:
            story.append(Paragraph(text, styles["texto"]))
    return story


# ── Public API ────────────────────────────────────────────────────────────────

TEMPLATES = {
    "classico":  _build_classico,
    "moderno":   _build_moderno,
    "executivo": _build_executivo,
}


def gerar_pdf_curriculo(texto_ou_json, template="classico"):
    texto, _ = extrair_texto_curriculo(texto_ou_json)
    texto = escape_xml(texto)
    blocks = _parse_curriculo(texto)

    FONT_DIR = _find_font_dir()
    _register_fonts(FONT_DIR)

    build_fn = TEMPLATES.get(template, _build_classico)
    story = build_fn(blocks)

    buffer = io.BytesIO()
    doc = _make_doc(buffer)
    doc.build(story)
    buffer.seek(0)
    return buffer
