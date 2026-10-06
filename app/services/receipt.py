from io import BytesIO
from pathlib import Path
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from flask import current_app, request, has_request_context


def public_origin():
    # In production Vercel supplies the real public Host. PUBLIC_APP_URL is only
    # a fallback for jobs where no HTTP request exists.
    origin = request.url_root.rstrip("/") if has_request_context() else ""
    return origin or current_app.config.get("PUBLIC_APP_URL", "").rstrip("/")


def verification_url(receipt):
    return f"{public_origin()}/verify/receipt/{receipt}"


def pdf(order, receipt):
    out = BytesIO(); c = canvas.Canvas(out, pagesize=A4); w, h = A4
    logo = Path(current_app.root_path).parent / "static" / "img" / "circulink-logo-transparent.png"
    if logo.exists(): c.drawImage(ImageReader(str(logo)), 50, h - 92, 82, 58, preserveAspectRatio=True, mask="auto")
    c.setFillColorRGB(.03, .34, .18); c.setFont("Helvetica-Bold", 20); c.drawString(145, h - 55, "CIRCULINK")
    c.setFillColorRGB(.05, .32, .57); c.setFont("Helvetica-Bold", 9); c.drawString(145, h - 72, "TUNA TAKA TAKA")
    c.setStrokeColorRGB(.82, .89, .85); c.line(50, h - 112, w - 50, h - 112)
    c.setFillColorRGB(.05, .14, .11); c.setFont("Helvetica-Bold", 17); c.drawString(50, h - 145, "PAYMENT RECEIPT")
    c.setFont("Helvetica", 9)
    c.drawString(50, h - 164, f"Receipt: {receipt}")
    c.drawString(50, h - 180, f"Order: {order.get('_id')}")
    c.drawString(50, h - 196, f"Payment: {order.get('payment_method', 'M-Pesa')}")
    y = h - 232
    c.setFont("Helvetica-Bold", 10); c.drawString(55, y, "ITEM"); c.drawRightString(w - 55, y, "AMOUNT")
    y -= 14; c.line(50, y, w - 50, y); y -= 18; c.setFont("Helvetica", 9)
    for item in order.get("items", []):
        c.drawString(55, y, str(item.get("title", "Material"))[:58])
        c.drawRightString(w - 55, y, f"KES {float(item.get('line_total', 0)):,.2f}"); y -= 17
    y -= 6; c.line(50, y, w - 50, y); y -= 22
    rows = [("Subtotal", order.get("subtotal", order.get("total", 0))),
            ("Service fee", order.get("service_fee", 0)), ("Pickup / delivery", order.get("pickup_fee", 0)),
            (f"Tax ({float(order.get('tax_percent', 0)):.2f}%)", order.get("tax", 0)), ("TOTAL", order.get("total", 0))]
    for label, amount in rows:
        c.setFont("Helvetica-Bold" if label == "TOTAL" else "Helvetica", 10 if label == "TOTAL" else 9)
        c.drawString(55, y, label); c.drawRightString(w - 55, y, f"KES {float(amount):,.2f}"); y -= 17
    c.setFont("Helvetica", 9); c.drawString(55, y - 4, f"M-Pesa receipt: {order.get('mpesa_receipt', receipt)}")
    qr = qrcode.make(verification_url(receipt)); qr_bytes = BytesIO(); qr.save(qr_bytes, "PNG"); qr_bytes.seek(0)
    c.drawImage(ImageReader(qr_bytes), w - 175, y - 125, 100, 100)
    c.setFont("Helvetica-Bold", 8); c.drawString(w - 175, y - 140, "SCAN TO VERIFY RECEIPT")
    c.setFont("Helvetica", 8); c.setFillColorRGB(.35, .42, .38)
    c.drawString(50, 65, "CIRCULINK · TUNA TAKA TAKA · Verified against the public CIRCULINK transaction record")
    c.drawString(50, 50, verification_url(receipt)[:110])
    c.save(); return out.getvalue()


def email(to, order, receipt):
    from app.services.email import send, _brand_html, _logo_inline
    from html import escape
    verify = verification_url(receipt)
    total = float(order.get("total", 0) or 0)
    mpesa = order.get("mpesa_receipt", receipt)
    body = f'''\
<div style="font-size:10px;color:#16845c;letter-spacing:1.5px;font-weight:800">PAYMENT CONFIRMED</div>
<h1 style="font-size:28px;margin:7px 0;color:#20372c">Your CIRCULINK receipt is ready</h1>
<p style="font-size:14px;line-height:1.7;color:#596a61">Thank you. Your payment has been recorded successfully. Your official PDF receipt is attached to this email.</p>
<table width="100%" cellpadding="0" cellspacing="0" style="margin:20px 0;border:1px solid #dfe8e3;border-radius:12px;background:#fbfdfc">
<tr><td style="padding:13px;font-size:11px;color:#7a8981">Receipt reference</td><td align="right" style="padding:13px;font-weight:bold">{escape(str(receipt))}</td></tr>
<tr><td style="padding:13px;border-top:1px solid #e7eeea;font-size:11px;color:#7a8981">M-Pesa receipt</td><td align="right" style="padding:13px;border-top:1px solid #e7eeea;font-weight:bold">{escape(str(mpesa))}</td></tr>
<tr><td style="padding:13px;border-top:1px solid #e7eeea;font-size:11px;color:#7a8981">Amount</td><td align="right" style="padding:13px;border-top:1px solid #e7eeea;font-size:18px;font-weight:800;color:#16845c">KES {total:,.2f}</td></tr>
</table>
<div style="text-align:center;margin:24px 0;padding:18px;background:#f7faf8;border:1px solid #e1e9e4;border-radius:12px">
<div style="font-size:11px;color:#596a61;margin-bottom:12px;font-weight:bold">SCAN TO VERIFY THIS RECEIPT</div>
<img src="cid:receipt-qr" width="150" height="150" alt="Receipt verification QR code" style="display:block;margin:auto">
<p style="font-size:10px;color:#7a8981;margin:10px 0 0">Or verify online using the button below.</p></div>
<div style="text-align:center"><a href="{escape(verify)}" style="display:inline-block;padding:12px 18px;background:#16845c;color:#fff;text-decoration:none;border-radius:8px;font-weight:bold;font-size:12px">Verify receipt online</a></div>
<p style="font-size:11px;color:#7a8981;line-height:1.6;margin-top:22px">If the attachment is unavailable, the verification page provides the official transaction status. Keep this email for your records.</p>
'''
    qr = qrcode.make(verify)
    qr_bytes = BytesIO(); qr.save(qr_bytes, "PNG"); qr_bytes.seek(0)
    return send(to, f"CIRCULINK · Payment receipt {receipt}", _brand_html("CIRCULINK payment receipt", "Your CIRCULINK payment has been confirmed", body),
                [(f"CIRCULINK-{receipt}.pdf", pdf(order, receipt), "application/pdf")],
                inline_images=_logo_inline() + [("receipt-qr", qr_bytes.getvalue(), "image/png")])

