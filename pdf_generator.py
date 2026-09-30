"""
Generate a simplified plain-language PDF using ReportLab.
Highlights red flags in red, uses clean typography.
"""
import io
import logging
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
    Table, TableStyle, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

logger = logging.getLogger(__name__)

SECTION_CONFIG = {
    'overview':     {'title': 'Document Overview',   'color': colors.HexColor('#1e293b'), 'icon': '📋'},
    'rights':       {'title': 'Your Rights',          'color': colors.HexColor('#0369a1'), 'icon': '✅'},
    'obligations':  {'title': 'Your Obligations',     'color': colors.HexColor('#7c3aed'), 'icon': '📌'},
    'risks':        {'title': 'Risks to Be Aware Of', 'color': colors.HexColor('#b45309'), 'icon': '⚠️'},
    'red_flags':    {'title': 'Red Flags',            'color': colors.HexColor('#dc2626'), 'icon': '🚩'},
}


def generate_simplified_pdf(document_title: str, summary: dict) -> bytes:
    """
    Generate a styled PDF summary and return as bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=22,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=6,
        fontName='Helvetica-Bold',
    )
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=20,
    )
    section_header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=13,
        spaceBefore=16,
        spaceAfter=8,
        fontName='Helvetica-Bold',
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=10,
        leading=16,
        textColor=colors.HexColor('#334155'),
        spaceAfter=4,
    )
    red_flag_style = ParagraphStyle(
        'RedFlag',
        parent=styles['Normal'],
        fontSize=10,
        leading=16,
        textColor=colors.HexColor('#dc2626'),
        spaceAfter=4,
        fontName='Helvetica-Bold',
    )
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#94a3b8'),
        alignment=TA_CENTER,
        spaceBefore=20,
    )

    story = []

    # Header
    story.append(Paragraph("⚖️ LexEasy", title_style))
    story.append(Paragraph(f"Plain-Language Summary: <b>{document_title}</b>", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
    story.append(Spacer(1, 0.3*cm))

    # Sections
    section_order = ['overview', 'rights', 'obligations', 'risks', 'red_flags']

    for key in section_order:
        cfg = SECTION_CONFIG[key]
        content = summary.get(key, '').strip()
        if not content:
            continue

        # Section heading with colour
        header_style = ParagraphStyle(
            f'Header_{key}',
            parent=section_header_style,
            textColor=cfg['color'],
        )
        story.append(Paragraph(f"{cfg['icon']}  {cfg['title']}", header_style))

        # Parse bullet lines
        lines = content.split('\n')
        is_red = key == 'red_flags'

        for line in lines:
            line = line.strip()
            if not line:
                story.append(Spacer(1, 0.1*cm))
                continue

            # Escape special XML characters for ReportLab
            line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            style = red_flag_style if is_red else body_style
            story.append(Paragraph(line, style))

        story.append(Spacer(1, 0.2*cm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#f1f5f9')))

    # Footer disclaimer
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        "⚠️  This summary is AI-generated for informational purposes only and does not constitute legal advice. "
        "Always consult a qualified lawyer before signing any legal document.",
        disclaimer_style
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()