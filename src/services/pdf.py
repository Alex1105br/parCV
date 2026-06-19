import io
import re

from src.services.parser import extrair_texto_curriculo
from src.utils import escape_xml

_URL_RE = re.compile(
    r'https?://[^\s<>"\',;]+'
    r'|(?:www\.|linkedin\.com|github\.com)[^\s<>"\',;]+'
    r'|[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[a-z]{2,}',
    re.IGNORECASE,
)


def _linkify(text):
    """Wrap URLs/emails in ReportLab <link> markup and style them."""
    def repl(m):
        raw = m.group(0)
        if '@' in raw and not raw.startswith('http'):
            href = 'mailto:' + raw
        elif not raw.startswith('http'):
            href = 'https://' + raw
        else:
            href = raw
        return f'<font color="#2c5282"><u><link href="{href}">{raw}</link></u></font>'
    return _URL_RE.sub(repl, text)


def _photo_header(header_paras, foto_bytes, page_width):
    """Return a Table with header paragraphs on the left and photo on the right."""
    from PIL import Image as PILImage
    from reportlab.lib.units import cm
    from reportlab.platypus import Table, TableStyle
    from reportlab.platypus import Image as RLImage

    PHOTO_W = 2.4 * cm
    pil_img = PILImage.open(io.BytesIO(foto_bytes))
    w, h = pil_img.size
    PHOTO_H = PHOTO_W if (w / h) >= 0.85 else PHOTO_W * (4 / 3)
    TEXT_W = page_width - PHOTO_W - 0.4 * cm

    photo = RLImage(io.BytesIO(foto_bytes), width=PHOTO_W, height=PHOTO_H)
    tbl = Table(
        [[header_paras, photo]],
        colWidths=[TEXT_W, PHOTO_W + 0.4 * cm],
    )
    tbl.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("ALIGN",         (1, 0), (1,  0), "RIGHT"),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
    ]))
    return tbl


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

def _build_classico(blocks, foto_bytes=None):
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import ParagraphStyle

    PRETO = colors.HexColor("#1a1a1a")
    CINZA = colors.HexColor("#555555")
    LINHA = colors.HexColor("#cccccc")
    AZUL  = colors.HexColor("#2c5282")
    PAGE_WIDTH = 21 * cm - 3.6 * cm

    def S(name, **kw):
        dict_styles = dict(fontName="Sans", textColor=PRETO, spaceAfter=2, spaceBefore=0, leading=14)
        dict_styles.update(kw)
        return ParagraphStyle(name, **dict_styles)

    styles = {
        "nome":    S("nome",    fontName="Sans-Bold",   fontSize=18, spaceAfter=6),
        "titulo":  S("titulo",  fontName="Sans-Italic", fontSize=10, spaceAfter=1, textColor=AZUL),
        "contato": S("contato", fontName="Sans",        fontSize=8.5, spaceAfter=8, textColor=CINZA),
        "secao":   S("secao",   fontName="Sans-Bold",   fontSize=9, spaceAfter=4, spaceBefore=14, textColor=AZUL),
        "empresa": S("empresa", fontName="Sans-Bold",   fontSize=9.5, spaceAfter=1, spaceBefore=8),
        "cargo":   S("cargo",   fontName="Sans-Italic", fontSize=9, spaceAfter=3, textColor=CINZA),
        "bullet":  S("bullet",  fontName="Sans",        fontSize=9, spaceAfter=2, leftIndent=10, leading=13),
        "texto":   S("texto",   fontName="Sans",        fontSize=9, spaceAfter=3, leading=13),
    }

    story = []
    header_paras = []
    in_header = True

    def _flush_header():
        nonlocal in_header
        if not in_header:
            return
        in_header = False
        if foto_bytes and header_paras:
            story.append(_photo_header(header_paras, foto_bytes, PAGE_WIDTH))
        else:
            story.extend(header_paras)

    for block in blocks:
        btype, text = block["type"], block["text"]
        if in_header and btype == "nome":
            header_paras.append(Paragraph(text, styles["nome"]))
        elif in_header and btype == "titulo":
            header_paras.append(Paragraph(text, styles["titulo"]))
        elif in_header and btype == "contato":
            header_paras.append(Paragraph(_linkify(text), styles["contato"]))
            _flush_header()
            story.append(HRFlowable(width="100%", thickness=1, color=PRETO, spaceAfter=6))
        elif btype == "secao":
            _flush_header()
            story.append(Paragraph(text, styles["secao"]))
            story.append(HRFlowable(width="100%", thickness=0.4, color=LINHA, spaceAfter=4))
        elif btype == "empresa":
            _flush_header()
            story.append(Spacer(1, 2))
            story.append(Paragraph(text, styles["empresa"]))
        elif btype == "cargo":
            _flush_header()
            story.append(Paragraph(text, styles["cargo"]))
        elif btype == "bullet":
            _flush_header()
            story.append(Paragraph(f"•  {text}", styles["bullet"]))
        else:
            _flush_header()
            story.append(Paragraph(text, styles["texto"]))

    _flush_header()
    return story


# ── Template: Moderno ─────────────────────────────────────────────────────────

def _build_moderno(blocks, foto_bytes=None):
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import ParagraphStyle

    TEAL     = colors.HexColor("#0d7377")
    PRETO    = colors.HexColor("#1a1a1a")
    CINZA    = colors.HexColor("#555555")
    BRANCO   = colors.HexColor("#ffffff")

    def S(name, **kw):
        dict_styles = dict(fontName="Sans", textColor=PRETO, spaceAfter=2, spaceBefore=0, leading=14)
        dict_styles.update(kw)
        return ParagraphStyle(name, **dict_styles)

    styles = {
        "nome":    S("nome-m",    fontName="Sans-Bold",   fontSize=20, spaceAfter=6, textColor=TEAL),
        "titulo":  S("titulo-m",  fontName="Sans-Italic", fontSize=10, spaceAfter=1, textColor=CINZA),
        "contato": S("contato-m", fontName="Sans",        fontSize=8.5, spaceAfter=10, textColor=CINZA),
        "secao":   S("secao-m",   fontName="Sans-Bold",   fontSize=8.5, spaceAfter=0, spaceBefore=0, textColor=BRANCO),
        "empresa": S("empresa-m", fontName="Sans-Bold",   fontSize=9.5, spaceAfter=1, spaceBefore=8),
        "cargo":   S("cargo-m",   fontName="Sans-Italic", fontSize=9, spaceAfter=3, textColor=CINZA),
        "bullet":  S("bullet-m",  fontName="Sans",        fontSize=9, spaceAfter=2, leftIndent=10, leading=13),
        "texto":   S("texto-m",   fontName="Sans",        fontSize=9, spaceAfter=3, leading=13),
    }

    PAGE_WIDTH = 21 * cm - 3.6 * cm

    story = []
    header_paras = []
    in_header = True

    def _flush_header():
        nonlocal in_header
        if not in_header:
            return
        in_header = False
        if foto_bytes and header_paras:
            story.append(_photo_header(header_paras, foto_bytes, PAGE_WIDTH))
        else:
            story.extend(header_paras)

    for block in blocks:
        btype, text = block["type"], block["text"]
        if in_header and btype == "nome":
            header_paras.append(Paragraph(text, styles["nome"]))
        elif in_header and btype == "titulo":
            header_paras.append(Paragraph(text, styles["titulo"]))
        elif in_header and btype == "contato":
            header_paras.append(Paragraph(_linkify(text), styles["contato"]))
            _flush_header()
        elif btype == "secao":
            _flush_header()
            p = Paragraph(f"  {text}", styles["secao"])
            tbl = Table([[p]], colWidths=[PAGE_WIDTH], rowHeights=[16])
            tbl.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1,-1), TEAL),
                ("TOPPADDING",    (0, 0), (-1,-1), 3),
                ("BOTTOMPADDING", (0, 0), (-1,-1), 3),
                ("LEFTPADDING",   (0, 0), (-1,-1), 6),
            ]))
            story.append(Spacer(1, 10))
            story.append(tbl)
            story.append(Spacer(1, 4))
        elif btype == "empresa":
            _flush_header()
            story.append(Spacer(1, 2))
            story.append(Paragraph(text, styles["empresa"]))
        elif btype == "cargo":
            _flush_header()
            story.append(Paragraph(text, styles["cargo"]))
        elif btype == "bullet":
            _flush_header()
            story.append(Paragraph(f"•  {text}", styles["bullet"]))
        else:
            _flush_header()
            story.append(Paragraph(text, styles["texto"]))

    _flush_header()
    return story


# ── Template: Executivo ───────────────────────────────────────────────────────

def _build_executivo(blocks, foto_bytes=None):
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import ParagraphStyle

    BURG     = colors.HexColor("#6b2737")
    CINZA_ESC= colors.HexColor("#2d2d2d")
    CINZA    = colors.HexColor("#666666")
    LINHA    = colors.HexColor("#dddddd")

    def S(name, **kw):
        dict_styles = dict(fontName="Sans", textColor=CINZA_ESC, spaceAfter=2, spaceBefore=0, leading=14)
        dict_styles.update(kw)
        return ParagraphStyle(name, **dict_styles)

    styles = {
        "nome":    S("nome-e",    fontName="Sans-Bold",   fontSize=19, spaceAfter=6, textColor=CINZA_ESC),
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
    header_paras = []
    in_header = True

    def _flush_header():
        nonlocal in_header
        if not in_header:
            return
        in_header = False
        if foto_bytes and header_paras:
            story.append(_photo_header(header_paras, foto_bytes, PAGE_WIDTH))
        else:
            story.extend(header_paras)

    for block in blocks:
        btype, text = block["type"], block["text"]
        if in_header and btype == "nome":
            header_paras.append(Paragraph(text, styles["nome"]))
        elif in_header and btype == "titulo":
            header_paras.append(Paragraph(text, styles["titulo"]))
        elif in_header and btype == "contato":
            header_paras.append(Paragraph(_linkify(text), styles["contato"]))
            _flush_header()
            story.append(HRFlowable(width="100%", thickness=1.5, color=BURG, spaceAfter=6))
        elif btype == "secao":
            _flush_header()
            story.append(Spacer(1, 10))
            accent = Table([[" ", Paragraph(text, styles["secao"])]], colWidths=[5, PAGE_WIDTH - 5])
            accent.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (0, 0), BURG),
                ("TOPPADDING",    (0, 0), (-1,-1), 3),
                ("BOTTOMPADDING", (0, 0), (-1,-1), 3),
                ("LEFTPADDING",   (0, 0), (-1,-1), 0),
                ("RIGHTPADDING",  (0, 0), (-1,-1), 0),
                ("LEFTPADDING",   (1, 0), (1, 0), 6),
                ("VALIGN",        (0, 0), (-1,-1), "MIDDLE"),
            ]))
            story.append(accent)
            story.append(HRFlowable(width="100%", thickness=0.4, color=LINHA, spaceAfter=4))
        elif btype == "empresa":
            _flush_header()
            story.append(Spacer(1, 2))
            story.append(Paragraph(text, styles["empresa"]))
        elif btype == "cargo":
            _flush_header()
            story.append(Paragraph(text, styles["cargo"]))
        elif btype == "bullet":
            _flush_header()
            story.append(Paragraph(f"▸  {text}", styles["bullet"]))
        else:
            _flush_header()
            story.append(Paragraph(text, styles["texto"]))

    _flush_header()
    return story


# ── Public API ────────────────────────────────────────────────────────────────

TEMPLATES = {
    "classico":  _build_classico,
    "moderno":   _build_moderno,
    "executivo": _build_executivo,
}


def gerar_pdf_curriculo(texto_ou_json, template="classico", foto_bytes=None):
    texto, _ = extrair_texto_curriculo(texto_ou_json)
    texto = escape_xml(texto)
    blocks = _parse_curriculo(texto)

    FONT_DIR = _find_font_dir()
    _register_fonts(FONT_DIR)

    build_fn = TEMPLATES.get(template, _build_classico)
    story = build_fn(blocks, foto_bytes=foto_bytes)

    buffer = io.BytesIO()
    doc = _make_doc(buffer)
    doc.build(story)
    buffer.seek(0)
    return buffer


def gerar_pdf_relatorio_entrevista(entrevista):
    """
    Gera PDF do relatório de entrevista com design dark inspirado na tela do sistema.
    Retorna bytes do PDF.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, PageBreak,
        Table, TableStyle, HRFlowable, Flowable
    )
    from reportlab.pdfgen import canvas as rl_canvas

    FONT_DIR = _find_font_dir()
    _register_fonts(FONT_DIR)

    # ── Paleta dark (espelha a tela) ──────────────────────────────────────────
    BG_PAGE      = colors.HexColor("#1a1a2e")
    BG_CARD      = colors.HexColor("#16213e")
    BG_CARD2     = colors.HexColor("#0f3460")
    TEXTO_CLARO  = colors.HexColor("#e2e8f0")
    TEXTO_MÉDIO  = colors.HexColor("#94a3b8")
    BORDA        = colors.HexColor("#334155")
    
    # Mapeamento das variáveis CSS
    PESSIMO      = colors.HexColor("#f87171")
    RUIM         = colors.HexColor("#fb923c")
    REGULAR      = colors.HexColor("#facc15")
    BOM          = colors.HexColor("#60a5fa")
    EXCELENTE    = colors.HexColor("#4ade80")

    PAGE_W, PAGE_H = A4
    MARGIN = 1.5 * cm
    CONTENT_W = PAGE_W - 2 * MARGIN

    # ── Classe customizada para desenhar fundos arredondados robustos ─────────
    class RoundedCard(Flowable):
        def __init__(self, content, width, bg_color, radius=10, border_color=None, border_width=0, padding=(12, 12, 12, 12), force_circle=False, forced_height=None):
            Flowable.__init__(self)
            self.content = content
            self.width = width
            self.bg_color = bg_color
            self.radius = radius
            self.border_color = border_color
            self.border_width = border_width
            self.force_circle = force_circle
            
            if isinstance(padding, (int, float)):
                self.padding = (padding, padding, padding, padding)
            else:
                self.padding = padding
            
            p_top, p_right, p_bottom, p_left = self.padding
            
            if isinstance(content, list):
                self.internal_table = Table([[c] for c in content], colWidths=[width - p_left - p_right])
                self.internal_table.setStyle(TableStyle([
                    ('LEFTPADDING', (0,0), (-1,-1), 0),
                    ('RIGHTPADDING', (0,0), (-1,-1), 0),
                    ('TOPPADDING', (0,0), (-1,-1), 0),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ]))
                self.content = self.internal_table

            if self.force_circle and forced_height:
                self.width = forced_height
                self.height = forced_height
                self.radius = forced_height / 2.0
                self.w, self.h = self.content.wrap(self.width - p_left - p_right, PAGE_H)
            else:
                self.w, self.h = self.content.wrap(width - p_left - p_right, PAGE_H)
                self.height = self.h + p_top + p_bottom

        def wrap(self, availWidth, availHeight):
            return self.width, self.height

        def draw(self):
            canvas = self.canv
            canvas.saveState()
            
            canvas.setFillColor(self.bg_color)
            if self.border_color and self.border_width > 0:
                canvas.setStrokeColor(self.border_color)
                canvas.setLineWidth(self.border_width)
                canvas.roundRect(0, 0, self.width, self.height, self.radius, fill=1, stroke=1)
            else:
                canvas.roundRect(0, 0, self.width, self.height, self.radius, fill=1, stroke=0)
            
            canvas.restoreState()
            p_top, p_right, p_bottom, p_left = self.padding
            
            offset_y = (self.height - self.h) / 2.0
            self.content.drawOn(canvas, p_left, offset_y)

    def dark_background(canv, doc):
        canv.saveState()
        canv.setFillColor(colors.HexColor("#1a1a2e"))
        canv.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
        canv.restoreState()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=1.4 * cm,
        bottomMargin=1.4 * cm,
    )

    def ps(name, font='Sans', size=10, color=TEXTO_CLARO,
            bold=False, after=6, before=0, leading=None, alignment=0):
        return ParagraphStyle(
            name,
            fontName='Sans-Bold' if bold else font,
            fontSize=size,
            textColor=color,
            spaceAfter=after,
            spaceBefore=before,
            alignment=alignment,
            leading=leading or (size * 1.35),
        )

    def get_status_info(score_val):
        try:
            val = float(score_val)
        except (ValueError, TypeError):
            val = 0.0
        if val >= 9.0: return ("Excelente", EXCELENTE, colors.Color(74/255, 222/255, 128/255, alpha=0.1))
        if val >= 7.0: return ("Bom", BOM, colors.Color(96/255, 165/255, 250/255, alpha=0.1))
        if val >= 5.0: return ("Regular", REGULAR, colors.Color(250/255, 204/255, 21/255, alpha=0.1))
        if val >= 3.0: return ("Ruim", RUIM, colors.Color(251/255, 146/255, 60/255, alpha=0.1))
        return ("Péssimo", PESSIMO, colors.Color(248/255, 113/255, 113/255, alpha=0.1))

    # ── Dados ─────────────────────────────────────────────────────────────────
    relatorio    = entrevista.relatorio_final
    score_geral  = relatorio.get("score_geral", 5.0)
    status_txt, s_cor, s_bg_alpha = get_status_info(score_geral)

    pontos_fortes  = relatorio.get("pontos_fortes", [])
    pontos_fracos  = relatorio.get("pontos_fracos", [])
    recomendacoes  = relatorio.get("recomendacoes", [])
    parecer        = relatorio.get("parecer_final", "Avaliação completa realizada.")

    story = []

    # ═══════════════════════════════════════════════════════════════════════════
    # CAIXA DO TÍTULO PRINCIPAL
    # ═══════════════════════════════════════════════════════════════════════════
    header_titulo = Paragraph(
        "Relatório de Desempenho da Entrevista",
        ps('h_titulo', bold=True, size=18, color=TEXTO_CLARO, after=0, alignment=1),
    )
    
    header_card = RoundedCard(header_titulo, CONTENT_W, BG_CARD2, radius=15, border_color=BORDA, border_width=0.5, padding=(22, 20, 22, 20))
    story.append(header_card)
    story.append(Spacer(1, 15))

    # ═══════════════════════════════════════════════════════════════════════════
    # CAIXA DA NOTA DA ENTREVISTA (ALINHAMENTO SIMÉTRICO E CENTRALIZADO DO SUBTEXTO)
    # ═══════════════════════════════════════════════════════════════════════════
    score_val_p = Paragraph(
        f"<b>{score_geral:.1f}</b>",
        ps('h_score_val', bold=True, size=22, color=TEXTO_CLARO, after=0, leading=22, alignment=1),
    )
    
    score_circle = RoundedCard(score_val_p, 1.8 * cm, colors.HexColor("#121829"), radius=9, border_color=s_cor, border_width=1.5, padding=(6, 2, 6, 2), force_circle=True, forced_height=1.8 * cm)

    # Combinamos "PONTUAÇÃO GERAL" e "(0 A 10)" com alignment=1 para garantir a simetria horizontal exata
    score_text_label = Paragraph(
        "PONTUAÇÃO GERAL<br/>(0 A 10)",
        ps('h_score_lbl', size=7, bold=True, color=TEXTO_MÉDIO, after=4, leading=10, alignment=1),
    )
    score_status_p = Paragraph(
        status_txt,
        ps('h_score_stat', bold=True, size=15, color=s_cor, after=0, leading=16, alignment=1),
    )
    
    score_info_tbl = Table([[score_text_label], [score_status_p]], colWidths=[3.4 * cm])
    score_info_tbl.setStyle(TableStyle([
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))

    score_group = Table([[score_circle, '', score_info_tbl]], colWidths=[1.8 * cm, 0.3 * cm, 3.4 * cm])
    score_group.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    
    score_box = RoundedCard(
        score_group, 
        6.3 * cm, 
        s_bg_alpha, 
        radius=16, 
        border_color=s_cor, 
        border_width=0.5, 
        padding=(12, 16, 12, 16)
    )

    wrapper_score = Table([[score_box]], colWidths=[CONTENT_W])
    wrapper_score.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    story.append(wrapper_score)
    story.append(Spacer(1, 20))

    # ─── TRÊS CARDS LADO A LADO ────────────────────────────────────────────────
    CARD_W = (CONTENT_W - 0.6 * cm) / 3

    def build_list_card(titulo, icone_cor, itens):
        rows = [Paragraph(titulo, ps(f'ct_{titulo}', bold=True, size=10, color=icone_cor, after=10))]
        for item in itens:
            rows.append(Paragraph(item, ps(f'ci_{titulo}_{item[:8]}', size=8.5, color=TEXTO_CLARO, after=8, leading=12)))
        if not itens:
            rows.append(Paragraph("—", ps('vazio', size=8.5, color=TEXTO_MÉDIO)))
        
        return RoundedCard(rows, CARD_W, BG_CARD, radius=10, border_color=BORDA, border_width=0.5, padding=15)

    card_fortes = build_list_card("Pontos Fortes", EXCELENTE, pontos_fortes)
    card_fracos = build_list_card("Pontos a Melhorar", RUIM, pontos_fracos)
    card_rec    = build_list_card("Recomendações", BOM, recomendacoes)

    tres_cards = Table([[card_fortes, card_fracos, card_rec]], colWidths=[CARD_W + 0.1*cm]*3)
    tres_cards.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(tres_cards)
    story.append(Spacer(1, 15))

    # ─── PARECER GERAL ─────────────────────────────────────────────────────────
    parecer_header_p = Paragraph("Parecer Geral", ps('ph', bold=True, size=11, color=TEXTO_CLARO, after=0))
    parecer_header_tbl = Table([[parecer_header_p]], colWidths=[CONTENT_W])
    parecer_header_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.Color(15/255, 52/255, 96/255, alpha=0.5)),
        ('LEFTPADDING', (0,0), (-1,-1), 20),
        ('TOPPADDING', (0,0), (-1,-1), 12),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, BORDA),
    ]))
    
    parecer_body = Paragraph(parecer, ps('pb', size=10, color=TEXTO_CLARO, after=0, leading=14))
    
    parecer_card_content = [
        parecer_header_tbl,
        Spacer(1, 15),
        Table([[parecer_body]], colWidths=[CONTENT_W-40], style=[('LEFTPADDING',(0,0),(-1,-1),20),('RIGHTPADDING',(0,0),(-1,-1),20)]),
        Spacer(1, 20)
    ]
    
    parecer_card = RoundedCard(parecer_card_content, CONTENT_W, BG_CARD, radius=10, border_color=BORDA, border_width=0.5, padding=0)
    story.append(parecer_card)
    story.append(Spacer(1, 25))

    # ─── DETALHES DAS PERGUNTAS ────────────────────────────────────────────────
    det_header = Paragraph("Detalhes das Perguntas", ps('dh', bold=True, size=14, color=TEXTO_CLARO, after=15))
    det_header_tbl = Table([[det_header]], colWidths=[CONTENT_W])
    det_header_tbl.setStyle(TableStyle([('LEFTPADDING', (0,0), (-1,-1), 12), ('LINEBEFORE', (0,0), (0,0), 4, BG_CARD2)]))
    story.append(det_header_tbl)
    story.append(Spacer(1, 10))

    for i, pergunta in enumerate(entrevista.perguntas, 1):
        av = pergunta.avaliacao_resposta or {}
        score = av.get("score", 0)
        
        _, q_color, q_bg_alpha = get_status_info(score)
        
        num_p = Paragraph(f"Pergunta {i}", ps(f'pnum{i}', bold=True, size=11, color=TEXTO_CLARO, after=0))
        badge_p = Paragraph(f"<b>{score}/10</b>", ps(f'pbadge{i}', bold=True, size=11, color=q_color, after=0))
        perg_hdr = Table([[num_p, badge_p]], colWidths=[CONTENT_W - 4 * cm, 3 * cm])
        perg_hdr.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.Color(15/255, 52/255, 96/255, alpha=0.4)),
            ('LEFTPADDING', (0,0), (-1,-1), 20),
            ('RIGHTPADDING', (0,0), (-1,-1), 20),
            ('TOPPADDING', (0,0), (-1,-1), 12),
            ('BOTTOMPADDING', (0,0), (-1,-1), 12),
            ('LINEBELOW', (0,0), (-1,-1), 0.5, BORDA),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ]))

        enunciado = Paragraph(pergunta.pergunta_principal, ps(f'ptxt{i}', bold=True, size=11, color=TEXTO_CLARO, after=15, leading=15))
        resp_label = Paragraph("SUA RESPOSTA", ps(f'rlbl{i}', bold=True, size=8, color=TEXTO_MÉDIO, after=6))
        resp_txt = Paragraph(pergunta.resposta_usuario or "Não fornecida.", ps(f'resp{i}', size=10, color=TEXTO_CLARO, leading=15))
        
        fb_label = Paragraph("FEEDBACK", ps(f'fblbl{i}', bold=True, size=8, color=q_color, after=6))
        fb_txt = Paragraph(av.get("feedback", "Sem feedback."), ps(f'fb{i}', size=10, color=TEXTO_CLARO, leading=15))
        fb_box = RoundedCard([fb_label, fb_txt], CONTENT_W - 2.2 * cm, q_bg_alpha, radius=6, border_color=q_color, border_width=0.5, padding=15)

        corpo_card = Table([
            [enunciado],
            [resp_label],
            [resp_txt],
            [Spacer(1, 15)],
            [fb_box]
        ], colWidths=[CONTENT_W - 1.2 * cm])
        corpo_card.setStyle(TableStyle([
            ('LEFTPADDING', (0,0), (-1,-1), 20),
            ('RIGHTPADDING', (0,0), (-1,-1), 20),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))

        perg_card = RoundedCard([perg_hdr, Spacer(1, 20), corpo_card, Spacer(1, 25)], CONTENT_W, BG_CARD, radius=10, border_color=BORDA, border_width=0.5, padding=0)
        story.append(perg_card)
        story.append(Spacer(1, 15))

    doc.build(story, onFirstPage=dark_background, onLaterPages=dark_background)
    buffer.seek(0)
    return buffer.getvalue()