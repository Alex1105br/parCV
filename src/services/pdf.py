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
        d = dict(fontName="Sans", textColor=PRETO, spaceAfter=2, spaceBefore=0, leading=14)
        d.update(kw)
        return ParagraphStyle(name, **d)

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
        d = dict(fontName="Sans", textColor=PRETO, spaceAfter=2, spaceBefore=0, leading=14)
        d.update(kw)
        return ParagraphStyle(name, **d)

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
                ("BACKGROUND",    (0, 0), (-1, -1), TEAL),
                ("TOPPADDING",    (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING",   (0, 0), (-1, -1), 6),
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
        d = dict(fontName="Sans", textColor=CINZA_ESC, spaceAfter=2, spaceBefore=0, leading=14)
        d.update(kw)
        return ParagraphStyle(name, **d)

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
    Gera PDF do relatório de entrevista em formato executivo.
    Retorna bytes do PDF.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, PageBreak, Table, TableStyle
    
    FONT_DIR = _find_font_dir()
    _register_fonts(FONT_DIR)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
    )
    
    # Cores
    AZUL_ESCURO = colors.HexColor("#0056b3")
    AZUL_CLARO = colors.HexColor("#007bff")
    VERDE = colors.HexColor("#28a745")
    AMARELO = colors.HexColor("#ffc107")
    VERMELHO = colors.HexColor("#dc3545")
    CINZA = colors.HexColor("#555555")
    CINZA_CLARO = colors.HexColor("#f9f9f9")
    
    # Estilos
    titulo_style = ParagraphStyle(
        'titulo',
        fontName='Sans-Bold',
        fontSize=18,
        textColor=AZUL_ESCURO,
        spaceAfter=12,
    )
    
    subtitulo_style = ParagraphStyle(
        'subtitulo',
        fontName='Sans-Bold',
        fontSize=13,
        textColor=AZUL_CLARO,
        spaceAfter=10,
        spaceBefore=12,
    )
    
    texto_style = ParagraphStyle(
        'texto',
        fontName='Sans',
        fontSize=10,
        textColor=CINZA,
        spaceAfter=8,
        leading=12,
    )
    
    # Story para o PDF
    story = []
    
    # ===== HEADER =====
    story.append(Paragraph("RELATÓRIO DE ENTREVISTA", titulo_style))
    story.append(Spacer(1, 8))
    
    # Score Geral
    relatorio = entrevista.relatorio_final
    score_geral = relatorio.get("score_geral", 5.0)
    
    # Determinar cor baseada no score
    if score_geral >= 7:
        score_cor = VERDE
    elif score_geral >= 4:
        score_cor = AMARELO
    else:
        score_cor = VERMELHO
    
    # Caixa de score
    score_text = Paragraph(f"<b>Score Final: {score_geral:.1f}/10</b>", ParagraphStyle(
        'score',
        fontName='Sans-Bold',
        fontSize=16,
        textColor=score_cor,
    ))
    
    score_table = Table([[score_text]], colWidths=[17 * cm])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f0f8ff")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('BORDER', (0, 0), (-1, -1), 2),
        ('BORDERCOLOR', (0, 0), (-1, -1), score_cor),
    ]))
    
    story.append(score_table)
    story.append(Spacer(1, 20))
    
    # ===== PARECER GERAL =====
    story.append(Paragraph("Parecer Geral", subtitulo_style))
    parecer = relatorio.get("parecer_final", "Avaliação completa realizada")
    story.append(Paragraph(parecer, texto_style))
    story.append(Spacer(1, 12))
    
    # ===== PONTOS FORTES =====
    story.append(Paragraph("Pontos Fortes", subtitulo_style))
    pontos_fortes = relatorio.get("pontos_fortes", [])
    for pf in pontos_fortes:
        story.append(Paragraph(f"✓ {pf}", texto_style))
    story.append(Spacer(1, 12))
    
    # ===== PONTOS A MELHORAR =====
    story.append(Paragraph("Pontos a Melhorar", subtitulo_style))
    pontos_fracos = relatorio.get("pontos_fracos", [])
    for pf in pontos_fracos:
        story.append(Paragraph(f"• {pf}", texto_style))
    story.append(Spacer(1, 12))
    
    # ===== RECOMENDAÇÕES =====
    story.append(Paragraph("Recomendações", subtitulo_style))
    recomendacoes = relatorio.get("recomendacoes", [])
    for rec in recomendacoes:
        story.append(Paragraph(f"→ {rec}", texto_style))
    
    story.append(PageBreak())
    
    # ===== PÁGINA 2: DETALHES DAS PERGUNTAS =====
    story.append(Paragraph("Detalhes das Respostas", titulo_style))
    story.append(Spacer(1, 12))
    
    for i, pergunta in enumerate(entrevista.perguntas, 1):
        story.append(Paragraph(f"<b>Pergunta {i}</b>", ParagraphStyle(
            f'pergunta_{i}',
            fontName='Sans-Bold',
            fontSize=11,
            textColor=AZUL_CLARO,
            spaceAfter=6,
        )))
        
        story.append(Paragraph(pergunta.pergunta_principal, texto_style))
        
        if pergunta.resposta_usuario:
            story.append(Paragraph(f"<b>Resposta:</b>", ParagraphStyle(
                'label',
                fontName='Sans-Bold',
                fontSize=10,
                textColor=CINZA,
            )))
            story.append(Paragraph(pergunta.resposta_usuario, texto_style))
        
        if pergunta.avaliacao_resposta:
            av = pergunta.avaliacao_resposta
            score = av.get("score", 5)
            feedback = av.get("feedback", "")
            
            score_cor = VERDE if score >= 7 else (AMARELO if score >= 4 else VERMELHO)
            
            story.append(Paragraph(
                f"<b>Avaliação: {score}/10</b>",
                ParagraphStyle(
                    f'av_score_{i}',
                    fontName='Sans-Bold',
                    fontSize=10,
                    textColor=score_cor,
                )
            ))
            
            story.append(Paragraph(feedback, texto_style))
        
        story.append(Spacer(1, 12))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
