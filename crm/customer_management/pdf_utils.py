import datetime
import io
import logging

from django.template.loader import render_to_string

from xhtml2pdf import pisa

logger = logging.getLogger(__name__)


def generate_quotation_pdf(quotation_version) -> bytes:
    """
    Generates PDF bytes for a specific QuotationVersion instance.
    Uses xhtml2pdf / WeasyPrint to render the HTML template.
    """
    quotation = quotation_version.quotation
    client_name = ""
    client_email = ""
    client_phone = ""
    company_name = ""

    if quotation.customer:
        client_name = quotation.customer.name
        client_email = quotation.customer.email
        client_phone = quotation.customer.phone
        company_name = quotation.customer.company_name or ""
    elif quotation.lead:
        client_name = quotation.lead.name
        client_email = quotation.lead.email or ""
        client_phone = quotation.lead.phone or ""
        company_name = quotation.lead.company_name or ""

    valid_until = quotation_version.created_at + datetime.timedelta(days=30)
    line_items = list(quotation_version.line_items.all())

    context = {
        "quotation": quotation,
        "version": quotation_version,
        "line_items": line_items,
        "client_name": client_name,
        "client_email": client_email,
        "client_phone": client_phone,
        "company_name": company_name,
        "valid_until": valid_until,
    }

    html_content = render_to_string("customer_management/quotation_pdf.html", context)

    try:
        import weasyprint
        return weasyprint.HTML(string=html_content).write_pdf()
    except Exception:
        result_buffer = io.BytesIO()
        pisa_status = pisa.CreatePDF(
            io.BytesIO(html_content.encode("utf-8")),
            dest=result_buffer
        )
        if pisa_status.err:
            raise RuntimeError("Failed to render PDF using xhtml2pdf.")
        return result_buffer.getvalue()
