"""
UNMASKED — Professional PDF Evidence Report Generator
Generates a forensic-grade PDF suitable for cyber crime cells and FIR filing.
"""

import io
import json
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.pdfgen import canvas

# Colors
DARK = HexColor('#2D2419')
ACCENT = HexColor('#C4704B')
MUTED = HexColor('#8B7D6B')
CREAM = HexColor('#FAF7F2')
BORDER = HexColor('#E8E0D4')
DANGER = HexColor('#A63D2F')
WARNING = HexColor('#D4A843')
SUCCESS = HexColor('#7A9E7E')
WHITE = HexColor('#FFFFFF')

# Styles
STYLES = {
    'title': ParagraphStyle(
        'title', fontName='Helvetica-Bold', fontSize=22,
        textColor=DARK, spaceAfter=4, leading=26,
    ),
    'subtitle': ParagraphStyle(
        'subtitle', fontName='Helvetica', fontSize=11,
        textColor=MUTED, spaceAfter=20, leading=14,
    ),
    'h1': ParagraphStyle(
        'h1', fontName='Helvetica-Bold', fontSize=14,
        textColor=ACCENT, spaceBefore=20, spaceAfter=8, leading=18,
    ),
    'h2': ParagraphStyle(
        'h2', fontName='Helvetica-Bold', fontSize=11,
        textColor=DARK, spaceBefore=14, spaceAfter=6, leading=14,
    ),
    'body': ParagraphStyle(
        'body', fontName='Helvetica', fontSize=9.5,
        textColor=DARK, spaceAfter=6, leading=14,
        alignment=TA_JUSTIFY,
    ),
    'body_bold': ParagraphStyle(
        'body_bold', fontName='Helvetica-Bold', fontSize=9.5,
        textColor=DARK, spaceAfter=6, leading=14,
    ),
    'small': ParagraphStyle(
        'small', fontName='Helvetica', fontSize=8,
        textColor=MUTED, spaceAfter=4, leading=10,
    ),
    'footer': ParagraphStyle(
        'footer', fontName='Helvetica', fontSize=7,
        textColor=MUTED, alignment=TA_CENTER,
    ),
    'disclaimer': ParagraphStyle(
        'disclaimer', fontName='Helvetica-Oblique', fontSize=8,
        textColor=MUTED, spaceAfter=4, leading=11,
        alignment=TA_JUSTIFY,
    ),
}


def _header_footer(canvas_obj, doc):
    canvas_obj.saveState()
    w, h = A4

    # Header line
    canvas_obj.setStrokeColor(ACCENT)
    canvas_obj.setLineWidth(1.5)
    canvas_obj.line(20 * mm, h - 18 * mm, w - 20 * mm, h - 18 * mm)

    # Header text
    canvas_obj.setFont('Helvetica-Bold', 10)
    canvas_obj.setFillColor(DARK)
    canvas_obj.drawString(20 * mm, h - 15 * mm, 'UNMASKED')

    canvas_obj.setFont('Helvetica', 7)
    canvas_obj.setFillColor(MUTED)
    canvas_obj.drawString(20 * mm, h - 11 * mm, 'Autonomous UPI Fraud Investigation System')

    canvas_obj.setFont('Helvetica', 7)
    canvas_obj.setFillColor(MUTED)
    canvas_obj.drawRightString(w - 20 * mm, h - 15 * mm, 'CONFIDENTIAL — LAW ENFORCEMENT USE')

    # Footer
    canvas_obj.setStrokeColor(BORDER)
    canvas_obj.setLineWidth(0.5)
    canvas_obj.line(20 * mm, 15 * mm, w - 20 * mm, 15 * mm)

    canvas_obj.setFont('Helvetica', 7)
    canvas_obj.setFillColor(MUTED)
    canvas_obj.drawString(20 * mm, 10 * mm, f'Generated: {datetime.now().strftime("%d %B %Y, %H:%M IST")}')
    canvas_obj.drawRightString(w - 20 * mm, 10 * mm, f'Page {doc.page}')

    canvas_obj.restoreState()


def _risk_label(score):
    if score >= 0.7: return 'HIGH RISK'
    if score >= 0.4: return 'MEDIUM RISK'
    if score >= 0.15: return 'LOW RISK'
    return 'UNKNOWN'


def _risk_color(score):
    if score >= 0.7: return DANGER
    if score >= 0.4: return WARNING
    if score >= 0.15: return ACCENT
    return MUTED


def generate_pdf(report_data: dict, case_data: dict = None) -> bytes:
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=22 * mm, bottomMargin=20 * mm,
        leftMargin=20 * mm, rightMargin=20 * mm,
    )

    story = []

    case_id = case_data.get('case_id', 'N/A') if case_data else 'N/A'
    fraud_vpa = case_data.get('fraud_vpa', 'N/A') if case_data else 'N/A'
    amount = case_data.get('amount', 0) if case_data else 0
    scam_pattern = report_data.get('scamPattern', report_data.get('scam_pattern', 'Unclassified'))
    confidence = report_data.get('confidenceOverall', report_data.get('confidence_overall', 0))
    network_size = report_data.get('networkSize', report_data.get('network_size', 0))
    trail_status = report_data.get('trailStatus', report_data.get('trail_status', 'unknown'))
    matched_advisory = report_data.get('matchedAdvisory', report_data.get('matched_advisory', ''))
    report_md = report_data.get('reportMarkdown', report_data.get('report_markdown', ''))
    graph_json = report_data.get('graphJson', report_data.get('graph_json', '{}'))

    # Parse graph data
    try:
        graph = json.loads(graph_json) if isinstance(graph_json, str) else graph_json
        nodes = graph.get('nodes', [])
        edges = graph.get('edges', [])
    except:
        nodes, edges = [], []

    # ─── COVER SECTION ───
    story.append(Spacer(1, 15 * mm))
    story.append(Paragraph('INVESTIGATION REPORT', STYLES['title']))
    story.append(Paragraph(
        f'Case {case_id[:8].upper()}  •  {datetime.now().strftime("%d %B %Y")}',
        STYLES['subtitle']
    ))

    # Case overview table
    overview_data = [
        ['CASE REFERENCE', str(case_id)[:36]],
        ['FRAUD VPA', fraud_vpa],
        ['AMOUNT', f'Rs {float(amount):,.2f}'],
        ['SCAM CLASSIFICATION', scam_pattern],
        ['CONFIDENCE', f'{float(confidence) * 100:.0f}%'],
        ['NETWORK SIZE', f'{network_size} connected accounts'],
        ['TRAIL STATUS', trail_status.replace('_', ' ').title()],
        ['MATCHED ADVISORY', matched_advisory or 'None'],
    ]

    overview_table = Table(overview_data, colWidths=[45 * mm, 120 * mm])
    overview_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), MUTED),
        ('TEXTCOLOR', (1, 0), (1, -1), DARK),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, BORDER),
        ('LINEBELOW', (0, -1), (-1, -1), 1, ACCENT),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(overview_table)
    story.append(Spacer(1, 8 * mm))

    # Disclaimer
    story.append(Paragraph(
        'This report is generated by an automated investigation system. All findings '
        'are based on transaction pattern analysis and should be verified by authorized '
        'law enforcement agencies. This report does not identify the real person behind '
        'any VPA — that requires bank KYC disclosure under legal authority.',
        STYLES['disclaimer']
    ))

    story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER, spaceAfter=5))

    # ─── MONEY TRAIL ───
    story.append(Paragraph('1. MONEY TRAIL', STYLES['h1']))

    # Parse hops from report markdown or graph
    hop_edges = [e for e in edges if any(
        n.get('depth', 99) == 0 and n.get('id') == e.get('source') for n in nodes
    )] if edges else []

    if trail_status and 'cold' in trail_status:
        story.append(Paragraph(
            f'The direct money trail for this transaction went cold ({trail_status.replace("_", " ")}). '
            f'However, network intelligence from prior investigations revealed '
            f'{network_size} connected accounts linked to the fraud VPA, indicating '
            f'this account is part of a larger syndicate.',
            STYLES['body']
        ))
    elif trail_status and 'cash_out' in trail_status:
        story.append(Paragraph(
            'A cash-out event was detected at the end of the transaction chain. '
            'The final recipient withdrew or converted the remaining funds, '
            'indicating the money has exited the UPI system.',
            STYLES['body']
        ))

    story.append(Spacer(1, 3 * mm))

    # ─── NETWORK ANALYSIS ───
    story.append(Paragraph('2. FRAUD NETWORK ANALYSIS', STYLES['h1']))
    story.append(Paragraph(
        f'The BFS (breadth-first search) traversal from the fraud VPA identified '
        f'{network_size} connected accounts across {len(set(n.get("bank", "") for n in nodes if n.get("bank")))} '
        f'banking platforms, with {len(edges)} transaction links between them.',
        STYLES['body']
    ))

    # High risk nodes table
    high_risk_nodes = sorted(
        [n for n in nodes if n.get('risk_score', 0) >= 0.5],
        key=lambda x: x.get('risk_score', 0),
        reverse=True
    )[:15]

    if high_risk_nodes:
        story.append(Paragraph('Key suspicious accounts:', STYLES['h2']))

        table_data = [['VPA', 'BANK', 'RISK', 'DEPTH', 'FLAGS']]
        for n in high_risk_nodes:
            risk = n.get('risk_score', 0)
            flags = ', '.join(f.replace('_', ' ') for f in (n.get('flags') or [])[:3])
            table_data.append([
                n.get('id', '')[:30],
                (n.get('bank') or 'Unknown')[:20],
                f'{risk * 100:.0f}%',
                f'Hop {n.get("depth", "?")}',
                flags[:40] or '—',
            ])

        node_table = Table(table_data, colWidths=[50 * mm, 35 * mm, 15 * mm, 15 * mm, 50 * mm])
        node_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 7.5),
            ('TEXTCOLOR', (0, 0), (-1, 0), MUTED),
            ('TEXTCOLOR', (0, 1), (-1, -1), DARK),
            ('BACKGROUND', (0, 0), (-1, 0), CREAM),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LINEBELOW', (0, 0), (-1, -1), 0.3, BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(node_table)
        story.append(Spacer(1, 3 * mm))

    # Cluster detection
    clusters = {}
    for n in nodes:
        name = n.get('id', '')
        prefix = name.split('@')[0].rstrip('0123456789').rstrip('_.')
        if len(prefix) >= 3:
            clusters.setdefault(prefix, []).append(n)

    syndicate_clusters = {k: v for k, v in clusters.items() if len(v) >= 3}
    if syndicate_clusters:
        story.append(Paragraph('Detected account clusters (potential syndicates):', STYLES['h2']))
        for prefix, members in sorted(syndicate_clusters.items(), key=lambda x: -len(x[1]))[:5]:
            vpa_list = ', '.join(m.get('id', '') for m in members[:6])
            if len(members) > 6:
                vpa_list += f' (+{len(members) - 6} more)'
            story.append(Paragraph(
                f'<b>"{prefix}" cluster ({len(members)} accounts):</b> {vpa_list}',
                STYLES['body']
            ))

    # ─── SCAM CLASSIFICATION ───
    story.append(Paragraph('3. SCAM CLASSIFICATION', STYLES['h1']))
    story.append(Paragraph(
        f'Pattern: <b>{scam_pattern}</b> (confidence: {float(confidence) * 100:.1f}%)',
        STYLES['body']
    ))
    if matched_advisory:
        story.append(Paragraph(
            f'Matched advisory: {matched_advisory}',
            STYLES['body']
        ))

    # ─── LEGAL FRAMEWORK ───
    story.append(Paragraph('4. APPLICABLE LEGAL FRAMEWORK', STYLES['h1']))

    legal_sections = [
        ['IT Act, Section 66', 'Computer-related offences — unauthorized access to payment systems', 'Up to 3 years + fine'],
        ['IT Act, Section 66C', 'Identity theft — using another person\'s UPI credentials', '3 years + Rs 1 lakh fine'],
        ['IT Act, Section 66D', 'Cheating by personation using computer resource', '3 years + Rs 1 lakh fine'],
        ['IPC Section 420 / BNS 318', 'Cheating and dishonestly inducing delivery of property', 'Up to 7 years + fine'],
        ['IPC Section 120B / BNS 61', 'Criminal conspiracy (if syndicate/mule network established)', 'Varies by underlying offence'],
    ]

    legal_table = Table(
        [['SECTION', 'DESCRIPTION', 'PENALTY']] + legal_sections,
        colWidths=[40 * mm, 80 * mm, 45 * mm]
    )
    legal_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('TEXTCOLOR', (0, 0), (-1, 0), MUTED),
        ('TEXTCOLOR', (0, 1), (0, -1), ACCENT),
        ('TEXTCOLOR', (1, 1), (-1, -1), DARK),
        ('BACKGROUND', (0, 0), (-1, 0), CREAM),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, 0), (-1, -1), 0.3, BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(legal_table)

    # ─── CONFIDENCE ASSESSMENT ───
    story.append(Paragraph('5. EVIDENCE CONFIDENCE ASSESSMENT', STYLES['h1']))

    conf_pct = float(confidence) * 100
    if conf_pct >= 70:
        conf_text = 'HIGH — Strong evidence chain with multiple corroborating signals.'
    elif conf_pct >= 40:
        conf_text = 'MODERATE — Reasonable evidence but some gaps in the trail.'
    else:
        conf_text = 'LOW — Limited direct evidence. Network intelligence provides supporting context.'

    story.append(Paragraph(f'Overall confidence: <b>{conf_pct:.0f}%</b> — {conf_text}', STYLES['body']))
    story.append(Spacer(1, 2 * mm))

    story.append(Paragraph('<b>Verified findings</b> (derived from transaction data):', STYLES['body']))
    story.append(Paragraph(
        '• Transaction chain structure and hop count  •  Account registration banks  '
        '•  Time deltas between transactions  •  Amount retention across hops  '
        '•  VPA registry risk scores from prior investigations',
        STYLES['small']
    ))

    story.append(Paragraph('<b>Inferred signals</b> (algorithmic assessment):', STYLES['body']))
    story.append(Paragraph(
        '• Mule confidence scores (weighted scoring model)  •  Scam pattern classification (RAG similarity)  '
        '•  Cluster detection (naming pattern analysis)  •  Cash-out probability',
        STYLES['small']
    ))

    # ─── RECOMMENDED ACTIONS ───
    story.append(Paragraph('6. RECOMMENDED ACTIONS', STYLES['h1']))

    actions = [
        'File FIR at the nearest cyber crime cell with this report as supporting evidence.',
        f'Request immediate account freeze for fraud VPA: {fraud_vpa}',
        'Submit complaint on cybercrime.gov.in (portal) or call 1930 (national helpline).',
    ]

    if high_risk_nodes:
        top_mules = ', '.join(n.get('id', '') for n in high_risk_nodes[:5])
        actions.append(f'Request freeze orders for high-risk mule accounts: {top_mules}')

    banks = list(set(n.get('bank', '') for n in nodes if n.get('bank') and n.get('risk_score', 0) > 0.5))
    if banks:
        actions.append(f'Issue Section 91 CrPC notices to: {", ".join(banks[:5])} for KYC disclosure.')

    actions.append('Preserve all digital evidence — screenshots, UPI app transaction history, call records.')
    actions.append('Request CCTV footage from ATM locations if cash-out detected.')

    for i, action in enumerate(actions, 1):
        story.append(Paragraph(f'{i}. {action}', STYLES['body']))

    # ─── END NOTE ───
    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width='100%', thickness=1, color=ACCENT, spaceAfter=8))
    story.append(Paragraph(
        'This report was generated by UNMASKED, an autonomous UPI fraud investigation system. '
        'It does not identify the real person behind any VPA — that requires bank KYC disclosure '
        'under legal authority (Section 91 CrPC / Section 94 BNSS). All confidence scores are '
        'algorithmic assessments and should be treated as investigative leads, not conclusive proof.',
        STYLES['disclaimer']
    ))
    story.append(Paragraph(
        'For questions about this report or the investigation methodology, '
        'contact the system administrator.',
        STYLES['disclaimer']
    ))

    # Build
    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)

    buffer.seek(0)
    return buffer.read()
