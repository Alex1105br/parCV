import io
import re

from src.services.parser import extrair_texto_curriculo
from src.utils import escape_xml


def _parse_curriculo(texto):
    """Parse structured CV text into a list of typed blocks.

    Returns a list of dicts with 'type' and 'text' keys.
    Types: nome, titulo, contato, secao, empresa, cargo, bullet, texto
    """
    blocks = []
    lines = texto.strip().split("\n")
    header_idx = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Section marker: ---SECAO: COMPETÊNCIAS---
        m = re.match(r"^---SECAO:\s*(.+?)\s*---$", line)
        if m:
            blocks.append({"type": "secao", "text": m.group(1).upper()})
            header_idx = 99
            continue

        # Company/institution marker: ---EMPRESA: Nome | Período---
        m = re.match(r"^---EMPRESA:\s*(.+?)\s*---$", line)
        if m:
            blocks.append({"type": "empresa", "text": m.group(1)})
            continue

        # Role/degree marker: ---CARGO: Título---
        m = re.match(r"^---CARGO:\s*(.+?)\s*---$", line)
        if m:
            blocks.append({"type": "cargo", "text": m.group(1)})
            continue

        # Bullet point
        if line.startswith("•") or line.startswith("-"):
            blocks.append({"type": "bullet", "text": line.lstrip("•- ").strip()})
            continue

        # Header lines (first 3 non-empty lines before any marker)
        if header_idx == 0:
            blocks.append({"type": "nome", "text": line})
            header_idx = 1
            continue
        if header_idx == 1:
            # Contact line or title
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

        # Fallback heuristics for unstructured text
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
    """Find Liberation Sans font directory across different distros."""
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
    # Fallback: search
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


def gerar_pdf_curriculo(texto_ou_json):
    """Generate a professional PDF from optimized curriculum text."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    texto, _ = extrair_texto_curriculo(texto_ou_json)
    texto = escape_xml(texto)
    blocks = _parse_curriculo(texto)

    FONT_DIR = _find_font_dir()
    pdfmetrics.registerFont(TTFont("Sans", FONT_DIR + "LiberationSans-Regular.ttf"))
    pdfmetrics.registerFont(TTFont("Sans-Bold", FONT_DIR + "LiberationSans-Bold.ttf"))
    pdfmetrics.registerFont(TTFont("Sans-Italic", FONT_DIR + "LiberationSans-Italic.ttf"))

    PRETO = colors.HexColor("#1a1a1a")
    CINZA = colors.HexColor("#555555")
    LINHA = colors.HexColor("#cccccc")
    AZUL = colors.HexColor("#2c5282")

    def S(name, **kw):
        d = dict(fontName="Sans", textColor=PRETO, spaceAfter=2, spaceBefore=0, leading=14)
        d.update(kw)
        return ParagraphStyle(name, **d)

    styles = {
        "nome": S("nome", fontName="Sans-Bold", fontSize=18, spaceAfter=2),
        "titulo": S("titulo", fontName="Sans-Italic", fontSize=10, spaceAfter=1, textColor=AZUL),
        "contato": S("contato", fontName="Sans", fontSize=8.5, spaceAfter=8, textColor=CINZA),
        "secao": S("secao", fontName="Sans-Bold", fontSize=9, spaceAfter=4, spaceBefore=14, textColor=AZUL),
        "empresa": S("empresa", fontName="Sans-Bold", fontSize=9.5, spaceAfter=1, spaceBefore=8),
        "cargo": S("cargo", fontName="Sans-Italic", fontSize=9, spaceAfter=3, textColor=CINZA),
        "bullet": S("bullet", fontName="Sans", fontSize=9, spaceAfter=2, leftIndent=10, leading=13),
        "texto": S("texto", fontName="Sans", fontSize=9, spaceAfter=3, leading=13),
    }

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
    )

    story = []
    prev_type = None

    for block in blocks:
        btype = block["type"]
        text = block["text"]

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

        prev_type = btype

    doc.build(story)
    buffer.seek(0)
    return buffer
