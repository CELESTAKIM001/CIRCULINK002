import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from flask import current_app
from html import escape


def _brand_html(title, preheader, body, accent="#16845c"):
    return f'''<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)}</title></head>
<body style="margin:0;background:#f3f7f4;font-family:Arial,Helvetica,sans-serif;color:#20372c">
<div style="display:none;max-height:0;overflow:hidden;opacity:0">{escape(preheader)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f3f7f4;padding:28px 10px"><tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:640px;background:#fff;border:1px solid #dce7e1;border-radius:16px;overflow:hidden">
<tr><td style="padding:22px 28px;border-bottom:1px solid #e7eeea;background:#fbfdfc">
<table width="100%"><tr><td><img src="cid:circulink-logo" alt="CIRCULINK" width="120" style="display:block;max-width:120px;height:auto"></td><td align="right" style="font-size:10px;letter-spacing:2px;color:#738179;font-weight:bold">TUNA TAKA TAKA</td></tr></table>
</td></tr>
<tr><td style="padding:30px 28px 24px">{body}</td></tr>
<tr><td style="padding:18px 28px;background:#f7faf8;border-top:1px solid #e7eeea;color:#738179;font-size:11px;line-height:1.6">
<strong style="color:{accent}">CIRCULINK</strong><br>Materials move. Value stays in the loop.<br>Built by GEOPRAM TECHNOLOGIES and friends during M-Hub 2026, Nyeri.
</td></tr></table></td></tr></table></body></html>'''


def send(to, subject, html, attachments=None, inline_images=None):
    """Send branded HTML email and fail gracefully. Email never becomes the source of truth."""
    c = current_app.config
    to = (to or "").strip()
    if not to:
        current_app.logger.warning("Email skipped: recipient is empty: %s", subject)
        return False
    if not c.get("SMTP_USERNAME") or not c.get("SMTP_PASSWORD"):
        current_app.logger.warning("SMTP not configured; email skipped: %s", subject)
        return False
    try:
        m = EmailMessage()
        m["Subject"] = subject
        m["From"] = c.get("SMTP_FROM") or c["SMTP_USERNAME"]
        m["To"] = to
        m.set_content("CIRCULINK notification. Please view this message in an HTML-capable email client.")
        m.add_alternative(html, subtype="html")
        html_part = m.get_payload()[1]
        for name, body, mime_type in attachments or []:
            maintype, subtype = mime_type.split("/", 1)
            m.add_attachment(body, maintype=maintype, subtype=subtype, filename=name)
        for cid, body, mime_type in inline_images or []:
            maintype, subtype = mime_type.split("/", 1)
            # Attach inline assets to the HTML alternative when possible.
            html_part.add_related(body, maintype=maintype, subtype=subtype, cid=f"<{cid}>", filename=cid)
        with smtplib.SMTP(c["SMTP_HOST"], c["SMTP_PORT"], timeout=30) as server:
            if c.get("SMTP_USE_TLS"):
                server.starttls(context=ssl.create_default_context())
            server.login(c["SMTP_USERNAME"], c["SMTP_PASSWORD"])
            server.send_message(m)
        return True
    except (OSError, smtplib.SMTPException) as exc:
        current_app.logger.exception("SMTP delivery failed for %s: %s", subject, exc)
        return False
    except Exception:
        current_app.logger.exception("Unexpected email delivery failure for %s", subject)
        return False


def send_otp(to, code):
    minutes = current_app.config["OTP_EXPIRY_MINUTES"]
    body = f'''
<div style="font-size:12px;color:#708078;letter-spacing:1.5px;font-weight:bold">SECURITY VERIFICATION</div>
<h1 style="font-size:27px;margin:8px 0 10px;color:#20372c">Verify your CIRCULINK account</h1>
<p style="font-size:14px;line-height:1.7;color:#596a61">Use the verification code below to continue. This code expires in <strong>{minutes} minutes</strong>.</p>
<div style="margin:24px 0;padding:20px;text-align:center;background:#edf8f1;border:1px solid #cfe8d9;border-radius:12px">
<div style="font-size:32px;letter-spacing:9px;font-weight:800;color:#16845c">{escape(code)}</div>
<div style="margin-top:8px;font-size:10px;color:#708078;letter-spacing:1px">ONE-TIME VERIFICATION CODE</div></div>
<p style="font-size:12px;line-height:1.6;color:#77857d">CIRCULINK will never ask you to share this code with another person. If you did not request this verification, you can safely ignore this email.</p>
'''
    return send(to, "CIRCULINK · Verify your email", _brand_html("Verify your CIRCULINK account", "Your one-time CIRCULINK verification code", body), inline_images=_logo_inline())


def _logo_inline():
    from pathlib import Path
    path = Path(current_app.root_path).parent / "static" / "img" / "circulink-logo-transparent.png"
    try:
        return [("circulink-logo", path.read_bytes(), "image/png")] if path.exists() else []
    except OSError:
        return []
