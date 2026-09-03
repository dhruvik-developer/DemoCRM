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
    gst_number = ""
    billing_address = ""

    if quotation.customer:
        client_name = quotation.customer.name
        client_email = quotation.customer.email
        client_phone = quotation.customer.phone
        company_name = quotation.customer.company_name or ""
        # Customer itself has no gst field, try linked lead's account
        if quotation.lead and quotation.lead.customer_account:
            gst_number = quotation.lead.customer_account.gst_number or ""
            billing_address = quotation.lead.customer_account.billing_address or ""
        if not gst_number and quotation.lead:
            gst_number = (quotation.lead.metadata or {}).get("gst_number", "") or (
                quotation.lead.metadata or {}
            ).get("gst", "")
            if not billing_address:
                billing_address = (quotation.lead.metadata or {}).get(
                    "billing_address", ""
                ) or (quotation.lead.metadata or {}).get("address", "")
    elif quotation.lead:
        client_name = quotation.lead.name
        client_email = quotation.lead.email or ""
        client_phone = quotation.lead.phone or ""
        company_name = quotation.lead.company_name or ""
        if quotation.lead.customer_account:
            gst_number = quotation.lead.customer_account.gst_number or ""
            billing_address = quotation.lead.customer_account.billing_address or ""
        if not gst_number:
            gst_number = (quotation.lead.metadata or {}).get("gst_number", "") or (
                quotation.lead.metadata or {}
            ).get("gst", "")
        if not billing_address:
            billing_address = (quotation.lead.metadata or {}).get(
                "billing_address", ""
            ) or (quotation.lead.metadata or {}).get("address", "")

    valid_until = quotation_version.created_at + datetime.timedelta(days=30)
    line_items = list(quotation_version.line_items.all())
    # GST split for display (CGST/SGST)
    from decimal import Decimal

    gst_rate = quotation_version.gst_rate or Decimal("0.00")
    gst_amount = quotation_version.gst_amount or Decimal("0.00")
    cgst_rate = (
        (gst_rate / Decimal("2")).quantize(Decimal("0.01"))
        if gst_rate
        else Decimal("0.00")
    )
    sgst_rate = cgst_rate
    cgst_amount = (
        (gst_amount / Decimal("2")).quantize(Decimal("0.01"))
        if gst_amount
        else Decimal("0.00")
    )
    sgst_amount = (
        (gst_amount - cgst_amount).quantize(Decimal("0.01"))
        if gst_amount
        else Decimal("0.00")
    )

    context = {
        "quotation": quotation,
        "version": quotation_version,
        "line_items": line_items,
        "client_name": client_name,
        "client_email": client_email,
        "client_phone": client_phone,
        "company_name": company_name,
        "gst_number": gst_number,
        "billing_address": billing_address,
        "company_gst": "27AABCD1234F1Z5",
        "company_cin": "U72200MH2020PTC123456",
        "valid_until": valid_until,
        "cgst_rate": cgst_rate,
        "sgst_rate": sgst_rate,
        "cgst_amount": cgst_amount,
        "sgst_amount": sgst_amount,
    }

    html_content = render_to_string("customer_management/quotation_pdf.html", context)

    # Prefer WeasyPrint (handles system fonts + U+20B9 correctly if DejaVu installed)
    try:
        import weasyprint

        return weasyprint.HTML(string=html_content).write_pdf()
    except Exception as e:
        logger.warning("WeasyPrint failed, falling back to xhtml2pdf: %s", e)
        # Register DejaVu for xhtml2pdf/ReportLab so ₹ (U+20B9) renders
        try:
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            import os

            dejavu = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            dejavu_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if os.path.exists(dejavu):
                pdfmetrics.registerFont(TTFont("DejaVu Sans", dejavu))
            if os.path.exists(dejavu_bold):
                pdfmetrics.registerFont(TTFont("DejaVu Sans Bold", dejavu_bold))
        except Exception as reg_err:
            logger.warning("Failed to register DejaVu font for xhtml2pdf: %s", reg_err)

        result_buffer = io.BytesIO()
        pisa_status = pisa.CreatePDF(
            io.BytesIO(html_content.encode("utf-8")), dest=result_buffer
        )
        if pisa_status.err:
            raise RuntimeError("Failed to render PDF using xhtml2pdf.")
        return result_buffer.getvalue()
