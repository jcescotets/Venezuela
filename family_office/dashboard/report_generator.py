"""
Report Generator — Genera reportes PDF del Family Office.
Produce informes ejecutivos para el Principal con análisis,
decisiones, vetos, y recomendaciones del CIO.
"""

from __future__ import annotations

import io
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# PDF generation with reportlab (lightweight HTML fallback if unavailable)
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


def generate_decision_pdf(record: dict[str, Any]) -> bytes:
    """
    Genera un PDF con el reporte de una decisión de inversión.
    Si reportlab no está disponible, genera HTML como fallback.
    """
    if HAS_REPORTLAB:
        return _generate_reportlab_pdf(record)
    return _generate_html_fallback(record)


def _generate_reportlab_pdf(record: dict[str, Any]) -> bytes:
    """Genera PDF usando reportlab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Title'],
        fontSize=18, spaceAfter=20,
        textColor=colors.HexColor('#1e293b'),
    )
    heading_style = ParagraphStyle(
        'CustomHeading', parent=styles['Heading2'],
        fontSize=13, spaceAfter=10, spaceBefore=15,
        textColor=colors.HexColor('#1e40af'),
    )
    body_style = ParagraphStyle(
        'CustomBody', parent=styles['Normal'],
        fontSize=10, spaceAfter=6,
        textColor=colors.HexColor('#334155'),
    )
    alert_style = ParagraphStyle(
        'AlertStyle', parent=styles['Normal'],
        fontSize=10, spaceAfter=6,
        textColor=colors.HexColor('#dc2626'),
    )

    elements = []

    # Title
    elements.append(Paragraph("FAMILY OFFICE — INFORME DE INVERSION", title_style))
    elements.append(Spacer(1, 10))

    # Date
    elements.append(Paragraph(
        f"Fecha: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}",
        body_style
    ))
    elements.append(Spacer(1, 15))

    # Proposal details
    elements.append(Paragraph("DETALLES DE LA PROPUESTA", heading_style))

    proposal_data = [
        ["Campo", "Valor"],
        ["Titulo", record.get("title", "N/A")],
        ["Clase de Activo", record.get("asset_class", "N/A")],
        ["Monto", f"USD {record.get('amount_usd', 0):,.0f}"],
        ["Jurisdiccion", record.get("jurisdiction", "N/A")],
        ["Estado", record.get("status", "N/A").upper()],
    ]

    table = Table(proposal_data, colWidths=[5 * cm, 10 * cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 15))

    # Analysis summary
    analyses_count = record.get("analyses_count", 0)
    vetoes_count = record.get("vetoes_count", 0)
    elements.append(Paragraph("RESUMEN DEL ANALISIS", heading_style))
    elements.append(Paragraph(
        f"Analisis completados: {analyses_count}",
        body_style
    ))

    # Vetoes
    vetoes = record.get("vetoes", [])
    if vetoes:
        elements.append(Paragraph("VETOS ACTIVOS", heading_style))
        for v in vetoes:
            agent = v.get("agent_role", "N/A")
            vtype = v.get("veto_type", "N/A")
            justification = v.get("justification", "N/A")
            severity = v.get("severity", 0)
            elements.append(Paragraph(
                f"<b>[{agent}]</b> {vtype} (Severidad: {severity * 100:.0f}%)",
                alert_style
            ))
            elements.append(Paragraph(f"  {justification}", body_style))
    else:
        elements.append(Paragraph("Sin vetos activos", body_style))

    # Committee Decision
    committee = record.get("committee", {})
    if committee:
        elements.append(Paragraph("DECISION DEL COMITE", heading_style))
        if committee.get("agreements"):
            elements.append(Paragraph("<b>Acuerdos:</b>", body_style))
            for a in committee["agreements"]:
                elements.append(Paragraph(f"  - {a}", body_style))
        if committee.get("contradictions"):
            elements.append(Paragraph("<b>Contradicciones:</b>", body_style))
            for c in committee["contradictions"]:
                elements.append(Paragraph(f"  - {c}", body_style))
        if committee.get("cio_synthesis"):
            elements.append(Paragraph("<b>Sintesis CIO:</b>", body_style))
            # Truncate long text for PDF
            synthesis = committee["cio_synthesis"][:1000]
            elements.append(Paragraph(synthesis, body_style))
        if committee.get("final_recommendation"):
            elements.append(Paragraph(
                f"<b>Recomendacion Final:</b> {committee['final_recommendation'][:500]}",
                body_style
            ))

    # Assumptions
    assumptions = record.get("assumptions", [])
    if assumptions:
        elements.append(Paragraph("SUPUESTOS CLAVE", heading_style))
        for a in assumptions:
            elements.append(Paragraph(f"  - {a}", body_style))

    # Outcome (if recorded)
    outcome = record.get("outcome")
    if outcome:
        elements.append(Paragraph("RESULTADO REGISTRADO", heading_style))
        elements.append(Paragraph(f"Descripcion: {outcome.get('description', 'N/A')}", body_style))
        if outcome.get("actual_return_pct") is not None:
            ret = outcome["actual_return_pct"]
            color = 'green' if ret >= 0 else 'red'
            elements.append(Paragraph(
                f"Retorno Real: <font color='{color}'>{ret:+.1f}%</font>",
                body_style
            ))
        lessons = outcome.get("lessons", [])
        if lessons:
            elements.append(Paragraph("<b>Lecciones:</b>", body_style))
            for l in lessons:
                elements.append(Paragraph(f"  - {l}", body_style))

    # Footer
    elements.append(Spacer(1, 30))
    footer_style = ParagraphStyle(
        'Footer', parent=styles['Normal'],
        fontSize=8, textColor=colors.HexColor('#94a3b8'),
    )
    elements.append(Paragraph(
        "Este documento fue generado automaticamente por el Family Office Agentico. "
        "Las recomendaciones no constituyen asesoramiento financiero.",
        footer_style
    ))

    doc.build(elements)
    return buffer.getvalue()


def _generate_html_fallback(record: dict[str, Any]) -> bytes:
    """Genera un reporte HTML cuando reportlab no está disponible."""
    status = record.get("status", "N/A").upper()
    status_color = "#22c55e" if status == "APPROVED" else "#ef4444" if status == "VETOED" else "#f59e0b"

    vetoes_html = ""
    for v in record.get("vetoes", []):
        vetoes_html += f"""
        <div style="background:#fef2f2;border-left:4px solid #ef4444;padding:12px;margin:8px 0;border-radius:4px;">
            <strong>[{v.get('agent_role','N/A')}]</strong> {v.get('veto_type','N/A')}
            (Severidad: {v.get('severity',0)*100:.0f}%)<br>
            <span style="color:#64748b;">{v.get('justification','N/A')}</span>
        </div>"""

    committee = record.get("committee", {})
    committee_html = ""
    if committee:
        if committee.get("cio_synthesis"):
            committee_html += f"<p><strong>Sintesis CIO:</strong> {committee['cio_synthesis'][:500]}</p>"
        if committee.get("final_recommendation"):
            committee_html += f"<p><strong>Recomendacion:</strong> {committee['final_recommendation'][:300]}</p>"

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Informe de Inversion</title>
<style>
body {{ font-family: 'Inter', Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 40px; color: #1e293b; }}
h1 {{ color: #1e40af; border-bottom: 3px solid #1e40af; padding-bottom: 10px; }}
h2 {{ color: #1e40af; margin-top: 30px; }}
table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
th {{ background: #1e40af; color: white; padding: 10px; text-align: left; }}
td {{ padding: 10px; border-bottom: 1px solid #e2e8f0; }}
tr:nth-child(even) {{ background: #f8fafc; }}
.status {{ display: inline-block; padding: 4px 12px; border-radius: 9999px; font-size: 0.8em; font-weight: 600; color: white; background: {status_color}; }}
.footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #e2e8f0; color: #94a3b8; font-size: 0.8em; }}
</style></head><body>
<h1>FAMILY OFFICE — INFORME DE INVERSION</h1>
<p>Fecha: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}</p>

<h2>Detalles de la Propuesta</h2>
<table>
<tr><th>Campo</th><th>Valor</th></tr>
<tr><td>Titulo</td><td>{record.get('title','N/A')}</td></tr>
<tr><td>Clase</td><td>{record.get('asset_class','N/A')}</td></tr>
<tr><td>Monto</td><td>USD {record.get('amount_usd',0):,.0f}</td></tr>
<tr><td>Jurisdiccion</td><td>{record.get('jurisdiction','N/A')}</td></tr>
<tr><td>Estado</td><td><span class="status">{status}</span></td></tr>
</table>

<h2>Analisis</h2>
<p>Analisis completados: {record.get('analyses_count',0)}</p>

<h2>Vetos</h2>
{vetoes_html or '<p>Sin vetos activos.</p>'}

<h2>Decision del Comite</h2>
{committee_html or '<p>Sin decision del comite disponible.</p>'}

<div class="footer">
Este documento fue generado automaticamente por el Family Office Agentico.
Las recomendaciones no constituyen asesoramiento financiero.
</div>
</body></html>"""

    return html.encode("utf-8")


def generate_portfolio_report(snapshot: dict[str, Any]) -> bytes:
    """Genera reporte del portfolio en HTML."""
    assets = snapshot.get("assets", [])
    total = snapshot.get("total_value_usd", 0)

    rows = ""
    for a in assets:
        pnl = (a.get("current_value_usd", 0) or 0) - (a.get("cost_basis_usd", 0) or 0)
        pnl_color = "#22c55e" if pnl >= 0 else "#ef4444"
        rows += f"""<tr>
            <td>{a.get('name','N/A')}</td>
            <td>{a.get('asset_class','N/A')}</td>
            <td>{a.get('jurisdiction','N/A')}</td>
            <td style="text-align:right">{a.get('quantity',0):,.2f}</td>
            <td style="text-align:right">USD {a.get('cost_basis_usd',0):,.0f}</td>
            <td style="text-align:right">USD {a.get('current_value_usd',0):,.0f}</td>
            <td style="text-align:right;color:{pnl_color}">USD {pnl:+,.0f}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Portfolio Report</title>
<style>
body {{ font-family: 'Inter', Arial, sans-serif; max-width: 1000px; margin: 0 auto; padding: 40px; color: #1e293b; }}
h1 {{ color: #1e40af; border-bottom: 3px solid #1e40af; padding-bottom: 10px; }}
table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
th {{ background: #1e40af; color: white; padding: 10px; text-align: left; font-size: 0.85em; }}
td {{ padding: 8px 10px; border-bottom: 1px solid #e2e8f0; font-size: 0.85em; }}
tr:nth-child(even) {{ background: #f8fafc; }}
.total {{ font-size: 1.5em; color: #22c55e; font-weight: bold; }}
.footer {{ margin-top: 40px; color: #94a3b8; font-size: 0.8em; }}
</style></head><body>
<h1>FAMILY OFFICE — PORTFOLIO REPORT</h1>
<p>Fecha: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}</p>
<p class="total">Valor Total: USD {total:,.0f}</p>
<p>Posiciones: {len(assets)}</p>

<table>
<tr><th>Activo</th><th>Clase</th><th>Jurisdiccion</th><th style="text-align:right">Cantidad</th>
<th style="text-align:right">Coste</th><th style="text-align:right">Valor</th><th style="text-align:right">P&L</th></tr>
{rows}
</table>

<div class="footer">
Generado automaticamente por el Family Office Agentico.
</div>
</body></html>"""

    return html.encode("utf-8")
