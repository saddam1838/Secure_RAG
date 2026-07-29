from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
import io


def generate_pdf_report(report_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("AI Security Assessment Report", styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(
        Paragraph(
            f"Score: {report_data['overall_security_score']}/100", styles["Heading2"]
        )
    )
    data = [["Metric", "Value"]]
    for k, v in report_data["security_metrics"].items():
        data.append([k, f"{v}%"])
    t = Table(data)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )
    story.append(t)
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
