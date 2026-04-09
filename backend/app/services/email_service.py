"""Email notification service using Resend API."""

import logging
import resend
from ..config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Configure Resend
resend.api_key = settings.resend_api_key


def _base_email_template(content: str) -> str:
    """Wrap content in a consistent branded HTML email layout."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>King Cap</title>
</head>
<body style="margin: 0; padding: 0; background-color: #F5F5F5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: #F5F5F5;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width: 600px; width: 100%; background-color: #FFFFFF; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
                    <!-- Header -->
                    <tr>
                        <td style="background-color: #1A1A1A; padding: 28px 40px; text-align: center;">
                            <h1 style="margin: 0; font-size: 28px; font-weight: 700; letter-spacing: 3px; color: #C6994A;">KING CAP</h1>
                        </td>
                    </tr>
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px;">
                            {content}
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #FAFAFA; padding: 24px 40px; border-top: 1px solid #EEEEEE; text-align: center;">
                            <p style="margin: 0 0 8px 0; font-size: 13px; color: #888888;">King Cap &mdash; Premium Custom Headwear</p>
                            <p style="margin: 0; font-size: 12px; color: #AAAAAA;">
                                <a href="{settings.store_frontend_url}" style="color: #C6994A; text-decoration: none;">Visit our store</a>
                                &nbsp;&middot;&nbsp;
                                <a href="{settings.store_frontend_url}/unsubscribe" style="color: #AAAAAA; text-decoration: none;">Unsubscribe</a>
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""


def _format_status(status: str) -> str:
    """Convert a status slug to a human-readable label."""
    return status.replace("_", " ").title()


def _cents_to_dollars(cents: int) -> str:
    """Format cents as a dollar string."""
    return f"${cents / 100:,.2f}"


def send_order_confirmation(
    to_email: str,
    order_number: str,
    items: list,
    total_cents: int,
) -> None:
    """Send an order confirmation email.

    Args:
        to_email: Recipient email address.
        order_number: The order number (e.g. KC-2026-00001).
        items: List of dicts with keys: name, quantity, unit_price (cents).
        total_cents: Order total in cents.
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping order confirmation email to %s", to_email)
        return

    # Build the items table rows
    item_rows = ""
    for item in items:
        name = item.get("name", "Custom Hat")
        qty = item.get("quantity", 1)
        unit_price = item.get("unit_price", 0)
        item_rows += f"""
        <tr>
            <td style="padding: 12px 0; border-bottom: 1px solid #EEEEEE; font-size: 14px; color: #1A1A1A;">{name}</td>
            <td style="padding: 12px 0; border-bottom: 1px solid #EEEEEE; font-size: 14px; color: #666666; text-align: center;">{qty}</td>
            <td style="padding: 12px 0; border-bottom: 1px solid #EEEEEE; font-size: 14px; color: #1A1A1A; text-align: right;">{_cents_to_dollars(unit_price * qty)}</td>
        </tr>"""

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">Order Confirmed</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">Thank you for your order! We've received your payment and your order is being processed.</p>

    <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 28px; border-radius: 0 4px 4px 0;">
        <p style="margin: 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Order Number</p>
        <p style="margin: 4px 0 0 0; font-size: 20px; font-weight: 700; color: #1A1A1A;">{order_number}</p>
    </div>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 24px;">
        <tr>
            <th style="padding: 0 0 8px 0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #888888; text-align: left; border-bottom: 2px solid #1A1A1A;">Item</th>
            <th style="padding: 0 0 8px 0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #888888; text-align: center; border-bottom: 2px solid #1A1A1A;">Qty</th>
            <th style="padding: 0 0 8px 0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #888888; text-align: right; border-bottom: 2px solid #1A1A1A;">Price</th>
        </tr>
        {item_rows}
    </table>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 28px;">
        <tr>
            <td style="padding: 12px 0 0 0; font-size: 16px; font-weight: 700; color: #1A1A1A;">Total</td>
            <td style="padding: 12px 0 0 0; font-size: 16px; font-weight: 700; color: #C6994A; text-align: right;">{_cents_to_dollars(total_cents)}</td>
        </tr>
    </table>

    <p style="margin: 0 0 24px 0; font-size: 14px; color: #666666;">We'll notify you when your order ships. You can track your order status at any time in your account.</p>

    <div style="text-align: center;">
        <a href="{settings.store_frontend_url}/account/orders" style="display: inline-block; background-color: #1A1A1A; color: #FFFFFF; padding: 14px 32px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 4px; letter-spacing: 0.5px;">View Your Order</a>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": f"Order Confirmed - {order_number}",
            "html": _base_email_template(content),
        })
        logger.info("Order confirmation email sent to %s for order %s", to_email, order_number)
    except Exception:
        logger.exception("Failed to send order confirmation email to %s for order %s", to_email, order_number)


def send_order_status_update(
    to_email: str,
    order_number: str,
    new_status: str,
    tracking_number: str | None = None,
    tracking_url: str | None = None,
) -> None:
    """Send an order status update email.

    Args:
        to_email: Recipient email address.
        order_number: The order number.
        new_status: The new status slug (e.g. "in_production", "shipped").
        tracking_number: Optional tracking number (for shipped status).
        tracking_url: Optional tracking URL (for shipped status).
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping status update email to %s", to_email)
        return

    # Status-specific messaging
    status_messages = {
        "confirmed": "Your order has been confirmed and payment received!",
        "in_production": "Your order is now being produced. Our team is carefully crafting your custom headwear.",
        "shipped": "Your order has shipped! It's on its way to you.",
        "delivered": "Your order has been delivered! We hope you love your new headwear.",
    }

    message = status_messages.get(new_status, f"Your order status has been updated to {_format_status(new_status)}.")
    formatted_status = _format_status(new_status)

    # Build tracking section for shipped orders
    tracking_section = ""
    if new_status == "shipped" and tracking_number:
        tracking_link = tracking_url or "#"
        tracking_section = f"""
        <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin: 20px 0; border-radius: 0 4px 4px 0;">
            <p style="margin: 0 0 4px 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Tracking Number</p>
            <p style="margin: 0;">
                <a href="{tracking_link}" style="font-size: 16px; font-weight: 600; color: #C6994A; text-decoration: none;">{tracking_number}</a>
            </p>
        </div>
        """

    # Status icon/color mapping
    status_colors = {
        "confirmed": "#2E7D32",
        "in_production": "#E65100",
        "shipped": "#1565C0",
        "delivered": "#2E7D32",
    }
    status_color = status_colors.get(new_status, "#C6994A")

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">Order Update</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">Here's an update on your order.</p>

    <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 20px; border-radius: 0 4px 4px 0;">
        <p style="margin: 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Order Number</p>
        <p style="margin: 4px 0 0 0; font-size: 20px; font-weight: 700; color: #1A1A1A;">{order_number}</p>
    </div>

    <div style="text-align: center; padding: 20px 0; margin-bottom: 20px;">
        <span style="display: inline-block; background-color: {status_color}; color: #FFFFFF; padding: 8px 20px; font-size: 14px; font-weight: 600; border-radius: 20px; letter-spacing: 0.5px;">{formatted_status}</span>
    </div>

    <p style="margin: 0 0 20px 0; font-size: 15px; color: #1A1A1A; line-height: 1.6;">{message}</p>

    {tracking_section}

    <div style="text-align: center; margin-top: 28px;">
        <a href="{settings.store_frontend_url}/account/orders" style="display: inline-block; background-color: #1A1A1A; color: #FFFFFF; padding: 14px 32px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 4px; letter-spacing: 0.5px;">View Your Order</a>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": f"Order {formatted_status} - {order_number}",
            "html": _base_email_template(content),
        })
        logger.info("Status update email sent to %s for order %s (status: %s)", to_email, order_number, new_status)
    except Exception:
        logger.exception("Failed to send status update email to %s for order %s", to_email, order_number)


def send_wholesale_application_received(to_email: str, company_name: str) -> None:
    """Send a confirmation that a wholesale application was received.

    Args:
        to_email: Recipient email address.
        company_name: The applicant's company name.
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping wholesale application email to %s", to_email)
        return

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">Application Received</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">Thank you for applying for a wholesale account.</p>

    <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
        <p style="margin: 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Company</p>
        <p style="margin: 4px 0 0 0; font-size: 18px; font-weight: 600; color: #1A1A1A;">{company_name}</p>
    </div>

    <p style="margin: 0 0 16px 0; font-size: 15px; color: #1A1A1A; line-height: 1.6;">We've received your wholesale application and our team is currently reviewing it. You can expect to hear back from us within 1-2 business days.</p>

    <p style="margin: 0 0 24px 0; font-size: 15px; color: #1A1A1A; line-height: 1.6;">Once approved, you'll have access to wholesale pricing and bulk ordering features.</p>

    <p style="margin: 0; font-size: 14px; color: #888888;">If you have any questions in the meantime, feel free to reply to this email.</p>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": "Wholesale Application Received - King Cap",
            "html": _base_email_template(content),
        })
        logger.info("Wholesale application email sent to %s for company %s", to_email, company_name)
    except Exception:
        logger.exception("Failed to send wholesale application email to %s", to_email)


def send_golf_application_received(to_email: str, course_name: str) -> None:
    """Send a confirmation that a golf pro-shop application was received.

    Args:
        to_email: Recipient email address.
        course_name: The golf course name.
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping golf application email to %s", to_email)
        return

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">Application Received</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">Thank you for applying for a golf pro-shop account.</p>

    <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
        <p style="margin: 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Golf Course</p>
        <p style="margin: 4px 0 0 0; font-size: 18px; font-weight: 600; color: #1A1A1A;">{course_name}</p>
    </div>

    <p style="margin: 0 0 16px 0; font-size: 15px; color: #1A1A1A; line-height: 1.6;">We've received your golf program application and our team is currently reviewing it. You can expect to hear back from us within 1-2 business days.</p>

    <p style="margin: 0 0 24px 0; font-size: 15px; color: #1A1A1A; line-height: 1.6;">Once approved, you'll have access to our golf pro-shop program with special pricing and custom branding options for your course.</p>

    <p style="margin: 0; font-size: 14px; color: #888888;">If you have any questions in the meantime, feel free to reply to this email.</p>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": "Golf Program Application Received - King Cap",
            "html": _base_email_template(content),
        })
        logger.info("Golf application email sent to %s for course %s", to_email, course_name)
    except Exception:
        logger.exception("Failed to send golf application email to %s", to_email)


def send_customer_account_created(
    to_email: str,
    first_name: str,
    temp_password: str,
    created_by: str,
) -> None:
    """Send email to a customer whose account was created by a salesperson."""
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping account created email to %s", to_email)
        return

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">Your Account Has Been Created</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">Hi {first_name}, a King Cap account has been set up for you by {created_by}.</p>

    <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
        <p style="margin: 0 0 4px 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Your Login Credentials</p>
        <p style="margin: 4px 0 0 0; font-size: 14px; color: #1A1A1A;"><strong>Email:</strong> {to_email}</p>
        <p style="margin: 4px 0 0 0; font-size: 14px; color: #1A1A1A;"><strong>Temporary Password:</strong> {temp_password}</p>
    </div>

    <p style="margin: 0 0 24px 0; font-size: 14px; color: #666666;">We recommend changing your password after your first login.</p>

    <div style="text-align: center;">
        <a href="{settings.store_frontend_url}/login" style="display: inline-block; background-color: #1A1A1A; color: #FFFFFF; padding: 14px 32px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 4px; letter-spacing: 0.5px;">Log In to Your Account</a>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": "Your King Cap Account Has Been Created",
            "html": _base_email_template(content),
        })
        logger.info("Account created email sent to %s", to_email)
    except Exception:
        logger.exception("Failed to send account created email to %s", to_email)


def send_welcome_email(to_email: str, first_name: str) -> None:
    """Send a welcome email to a newly registered user.

    Args:
        to_email: Recipient email address.
        first_name: The user's first name.
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping welcome email to %s", to_email)
        return

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">Welcome to King Cap, {first_name}!</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">Your account has been created and you're all set to start shopping.</p>

    <p style="margin: 0 0 16px 0; font-size: 15px; color: #1A1A1A; line-height: 1.6;">Here's what you can do with your King Cap account:</p>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 24px;">
        <tr>
            <td style="padding: 12px 0; border-bottom: 1px solid #EEEEEE;">
                <span style="display: inline-block; width: 8px; height: 8px; background-color: #C6994A; border-radius: 50%; margin-right: 12px; vertical-align: middle;"></span>
                <span style="font-size: 14px; color: #1A1A1A; vertical-align: middle;">Browse our premium custom headwear collection</span>
            </td>
        </tr>
        <tr>
            <td style="padding: 12px 0; border-bottom: 1px solid #EEEEEE;">
                <span style="display: inline-block; width: 8px; height: 8px; background-color: #C6994A; border-radius: 50%; margin-right: 12px; vertical-align: middle;"></span>
                <span style="font-size: 14px; color: #1A1A1A; vertical-align: middle;">Customize hats with your own designs and logos</span>
            </td>
        </tr>
        <tr>
            <td style="padding: 12px 0; border-bottom: 1px solid #EEEEEE;">
                <span style="display: inline-block; width: 8px; height: 8px; background-color: #C6994A; border-radius: 50%; margin-right: 12px; vertical-align: middle;"></span>
                <span style="font-size: 14px; color: #1A1A1A; vertical-align: middle;">Track your orders from production to delivery</span>
            </td>
        </tr>
        <tr>
            <td style="padding: 12px 0;">
                <span style="display: inline-block; width: 8px; height: 8px; background-color: #C6994A; border-radius: 50%; margin-right: 12px; vertical-align: middle;"></span>
                <span style="font-size: 14px; color: #1A1A1A; vertical-align: middle;">Apply for wholesale or golf pro-shop pricing</span>
            </td>
        </tr>
    </table>

    <div style="text-align: center;">
        <a href="{settings.store_frontend_url}" style="display: inline-block; background-color: #1A1A1A; color: #FFFFFF; padding: 14px 32px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 4px; letter-spacing: 0.5px;">Start Shopping</a>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": f"Welcome to King Cap, {first_name}!",
            "html": _base_email_template(content),
        })
        logger.info("Welcome email sent to %s", to_email)
    except Exception:
        logger.exception("Failed to send welcome email to %s", to_email)


def send_sample_request_confirmation(
    to_email: str,
    first_name: str,
    sample_number: str,
    product_name: str,
    sample_type: str,
    quantity: int,
) -> None:
    """Send confirmation that a sample request was received."""
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping sample confirmation email to %s", to_email)
        return

    type_label = "Custom Decorated" if sample_type == "custom" else "Blank"

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">Sample Request Received</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">Hi {first_name}, your sample request has been submitted and is under review.</p>

    <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
        <p style="margin: 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Sample Number</p>
        <p style="margin: 4px 0 0 0; font-size: 20px; font-weight: 700; color: #1A1A1A;">{sample_number}</p>
    </div>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 24px;">
        <tr>
            <td style="padding: 8px 0; font-size: 14px; color: #888888; width: 120px;">Product</td>
            <td style="padding: 8px 0; font-size: 14px; color: #1A1A1A; font-weight: 600;">{product_name}</td>
        </tr>
        <tr>
            <td style="padding: 8px 0; font-size: 14px; color: #888888;">Type</td>
            <td style="padding: 8px 0; font-size: 14px; color: #1A1A1A;">{type_label}</td>
        </tr>
        <tr>
            <td style="padding: 8px 0; font-size: 14px; color: #888888;">Quantity</td>
            <td style="padding: 8px 0; font-size: 14px; color: #1A1A1A;">{quantity}</td>
        </tr>
    </table>

    <p style="margin: 0; font-size: 14px; color: #666666;">We'll notify you once your sample has been approved and is ready to ship.</p>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": f"Sample Request {sample_number} - King Cap",
            "html": _base_email_template(content),
        })
        logger.info("Sample confirmation email sent to %s for sample %s", to_email, sample_number)
    except Exception:
        logger.exception("Failed to send sample confirmation email to %s", to_email)


def send_sample_status_update(
    to_email: str,
    first_name: str,
    sample_number: str,
    new_status: str,
    tracking_number: str | None = None,
    tracking_url: str | None = None,
) -> None:
    """Send a sample request status update email."""
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping sample status email to %s", to_email)
        return

    formatted_status = _format_status(new_status)

    tracking_section = ""
    if new_status == "shipped" and tracking_number:
        tracking_link = tracking_url or "#"
        tracking_section = f"""
        <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin: 20px 0; border-radius: 0 4px 4px 0;">
            <p style="margin: 0 0 4px 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Tracking Number</p>
            <p style="margin: 0;">
                <a href="{tracking_link}" style="font-size: 16px; font-weight: 600; color: #C6994A; text-decoration: none;">{tracking_number}</a>
            </p>
        </div>
        """

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">Sample Request Update</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">Hi {first_name}, here's an update on your sample request.</p>

    <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 20px; border-radius: 0 4px 4px 0;">
        <p style="margin: 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Sample Number</p>
        <p style="margin: 4px 0 0 0; font-size: 20px; font-weight: 700; color: #1A1A1A;">{sample_number}</p>
    </div>

    <div style="text-align: center; padding: 20px 0;">
        <span style="display: inline-block; background-color: #1A1A1A; color: #FFFFFF; padding: 8px 20px; font-size: 14px; font-weight: 600; border-radius: 20px; letter-spacing: 0.5px;">{formatted_status}</span>
    </div>

    {tracking_section}
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": f"Sample {formatted_status} - {sample_number}",
            "html": _base_email_template(content),
        })
        logger.info("Sample status email sent to %s for sample %s (status: %s)", to_email, sample_number, new_status)
    except Exception:
        logger.exception("Failed to send sample status email to %s", to_email)


def send_email_verification(to_email: str, first_name: str, verification_url: str) -> None:
    """Send an email verification link to a newly registered user.

    Args:
        to_email: Recipient email address.
        first_name: The user's first name.
        verification_url: The URL to verify the email address.
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping verification email to %s", to_email)
        return

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">Verify Your Email</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">Hi {first_name}, thanks for creating a King Cap account! Please verify your email address to get started.</p>

    <div style="text-align: center; margin: 32px 0;">
        <a href="{verification_url}" style="display: inline-block; background-color: #C6994A; color: #FFFFFF; padding: 14px 32px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 4px; letter-spacing: 0.5px;">Verify Email Address</a>
    </div>

    <p style="margin: 0 0 16px 0; font-size: 14px; color: #666666;">If the button above doesn't work, copy and paste this link into your browser:</p>
    <p style="margin: 0 0 24px 0; font-size: 13px; color: #C6994A; word-break: break-all;">{verification_url}</p>

    <p style="margin: 0; font-size: 13px; color: #888888;">This link will expire in 24 hours. If you didn't create an account, you can safely ignore this email.</p>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": "Verify Your Email - King Cap",
            "html": _base_email_template(content),
        })
        logger.info("Verification email sent to %s", to_email)
    except Exception:
        logger.exception("Failed to send verification email to %s", to_email)


def send_password_reset_email(to_email: str, first_name: str, reset_url: str) -> None:
    """Send a password reset link.

    Args:
        to_email: Recipient email address.
        first_name: The user's first name.
        reset_url: The URL to reset the password.
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping password reset email to %s", to_email)
        return

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">Reset Your Password</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">Hi {first_name}, we received a request to reset your password. Click the button below to choose a new one.</p>

    <div style="text-align: center; margin: 32px 0;">
        <a href="{reset_url}" style="display: inline-block; background-color: #C6994A; color: #FFFFFF; padding: 14px 32px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 4px; letter-spacing: 0.5px;">Reset Password</a>
    </div>

    <p style="margin: 0 0 16px 0; font-size: 14px; color: #666666;">If the button above doesn't work, copy and paste this link into your browser:</p>
    <p style="margin: 0 0 24px 0; font-size: 13px; color: #C6994A; word-break: break-all;">{reset_url}</p>

    <p style="margin: 0; font-size: 13px; color: #888888;">This link will expire in 1 hour. If you didn't request a password reset, you can safely ignore this email.</p>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": "Reset Your Password - King Cap",
            "html": _base_email_template(content),
        })
        logger.info("Password reset email sent to %s", to_email)
    except Exception:
        logger.exception("Failed to send password reset email to %s", to_email)


def send_password_changed(to_email: str, first_name: str) -> None:
    """Send a confirmation that the password was changed.

    Args:
        to_email: Recipient email address.
        first_name: The user's first name.
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping password changed email to %s", to_email)
        return

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">Password Changed</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">Hi {first_name}, your password has been successfully changed.</p>

    <p style="margin: 0 0 16px 0; font-size: 15px; color: #1A1A1A; line-height: 1.6;">You can now log in with your new password.</p>

    <p style="margin: 0 0 24px 0; font-size: 14px; color: #666666;">If you didn't make this change, please contact us immediately.</p>

    <div style="text-align: center;">
        <a href="{settings.store_frontend_url}/login" style="display: inline-block; background-color: #1A1A1A; color: #FFFFFF; padding: 14px 32px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 4px; letter-spacing: 0.5px;">Log In</a>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": "Password Changed - King Cap",
            "html": _base_email_template(content),
        })
        logger.info("Password changed email sent to %s", to_email)
    except Exception:
        logger.exception("Failed to send password changed email to %s", to_email)


def send_application_approved(
    to_email: str,
    first_name: str,
    account_type: str,
    verification_url: str | None = None,
) -> None:
    """Send an application approval notification.

    Args:
        to_email: Recipient email address.
        first_name: The user's first name.
        account_type: "wholesale" or "golf".
        verification_url: Optional verification URL if email not yet verified.
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping approval email to %s", to_email)
        return

    account_label = "Wholesale" if account_type == "wholesale" else "Golf Pro-Shop"

    verification_section = ""
    if verification_url:
        verification_section = f"""
        <div style="background-color: #FFF8E1; border-left: 4px solid #F9A825; padding: 16px 20px; margin: 20px 0; border-radius: 0 4px 4px 0;">
            <p style="margin: 0 0 8px 0; font-size: 14px; font-weight: 600; color: #1A1A1A;">Verify your email to get started</p>
            <p style="margin: 0;">
                <a href="{verification_url}" style="font-size: 14px; font-weight: 600; color: #C6994A; text-decoration: none;">Click here to verify your email &rarr;</a>
            </p>
        </div>
        """

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">Application Approved!</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">Hi {first_name}, great news! Your {account_label} application has been approved.</p>

    <div style="background-color: #E8F5E9; border-left: 4px solid #2E7D32; padding: 16px 20px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
        <p style="margin: 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Status</p>
        <p style="margin: 4px 0 0 0; font-size: 18px; font-weight: 600; color: #2E7D32;">Approved</p>
    </div>

    {verification_section}

    <p style="margin: 0 0 16px 0; font-size: 15px; color: #1A1A1A; line-height: 1.6;">You now have access to {account_label.lower()} pricing and features. Log in to your account to start ordering.</p>

    <div style="text-align: center;">
        <a href="{settings.store_frontend_url}/login" style="display: inline-block; background-color: #1A1A1A; color: #FFFFFF; padding: 14px 32px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 4px; letter-spacing: 0.5px;">Log In to Your Account</a>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": f"{account_label} Application Approved - King Cap",
            "html": _base_email_template(content),
        })
        logger.info("Application approval email sent to %s (type: %s)", to_email, account_type)
    except Exception:
        logger.exception("Failed to send approval email to %s", to_email)


def send_application_rejected(
    to_email: str,
    first_name: str,
    account_type: str,
    reason: str | None = None,
) -> None:
    """Send an application rejection notification.

    Args:
        to_email: Recipient email address.
        first_name: The user's first name.
        account_type: "wholesale" or "golf".
        reason: Optional reason for rejection.
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping rejection email to %s", to_email)
        return

    account_label = "Wholesale" if account_type == "wholesale" else "Golf Pro-Shop"

    reason_section = ""
    if reason:
        reason_section = f"""
        <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin: 20px 0; border-radius: 0 4px 4px 0;">
            <p style="margin: 0 0 4px 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Additional Notes</p>
            <p style="margin: 0; font-size: 14px; color: #1A1A1A; line-height: 1.6;">{reason}</p>
        </div>
        """

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">Application Update</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">Hi {first_name}, thank you for your interest in our {account_label.lower()} program.</p>

    <p style="margin: 0 0 16px 0; font-size: 15px; color: #1A1A1A; line-height: 1.6;">After reviewing your application, we're unable to approve it at this time.</p>

    {reason_section}

    <p style="margin: 0 0 24px 0; font-size: 14px; color: #666666;">You can still shop as a retail customer. If you have any questions or would like to discuss your application, please reply to this email.</p>

    <div style="text-align: center;">
        <a href="{settings.store_frontend_url}" style="display: inline-block; background-color: #1A1A1A; color: #FFFFFF; padding: 14px 32px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 4px; letter-spacing: 0.5px;">Visit Our Store</a>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": f"{account_label} Application Update - King Cap",
            "html": _base_email_template(content),
        })
        logger.info("Application rejection email sent to %s (type: %s)", to_email, account_type)
    except Exception:
        logger.exception("Failed to send rejection email to %s", to_email)


def send_new_application_alert(
    to_email: str,
    customer_name: str,
    company_name: str,
    account_type: str,
) -> None:
    """Send a notification to staff about a new application.

    Args:
        to_email: Staff member's email address.
        customer_name: The applicant's full name.
        company_name: The applicant's company/course name.
        account_type: "wholesale" or "golf".
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping application alert email to %s", to_email)
        return

    account_label = "Wholesale" if account_type == "wholesale" else "Golf Pro-Shop"

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">New {account_label} Application</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">A new {account_label.lower()} application has been submitted and is awaiting review.</p>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 24px;">
        <tr>
            <td style="padding: 8px 0; font-size: 14px; color: #888888; width: 120px;">Applicant</td>
            <td style="padding: 8px 0; font-size: 14px; color: #1A1A1A; font-weight: 600;">{customer_name}</td>
        </tr>
        <tr>
            <td style="padding: 8px 0; font-size: 14px; color: #888888;">Company</td>
            <td style="padding: 8px 0; font-size: 14px; color: #1A1A1A;">{company_name}</td>
        </tr>
        <tr>
            <td style="padding: 8px 0; font-size: 14px; color: #888888;">Type</td>
            <td style="padding: 8px 0; font-size: 14px; color: #1A1A1A;">{account_label}</td>
        </tr>
    </table>

    <div style="text-align: center;">
        <a href="{settings.store_frontend_url}/admin/applications" style="display: inline-block; background-color: #1A1A1A; color: #FFFFFF; padding: 14px 32px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 4px; letter-spacing: 0.5px;">Review Application</a>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": f"New {account_label} Application - {customer_name}",
            "html": _base_email_template(content),
        })
        logger.info("Application alert email sent to staff %s for applicant %s", to_email, customer_name)
    except Exception:
        logger.exception("Failed to send application alert email to %s", to_email)


# ---------------------------------------------------------------------------
# New Order Alert (STAFF)
# ---------------------------------------------------------------------------

def send_new_order_alert(
    to_email: str,
    order_number: str,
    customer_name: str,
    total_cents: int,
) -> None:
    """Send a staff notification about a new order.

    Args:
        to_email: Staff recipient email address.
        order_number: The order number.
        customer_name: The customer's full name.
        total_cents: Order total in cents.
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping new order alert to %s", to_email)
        return

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">New Order Received</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">A new order has been placed and needs attention.</p>

    <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
        <p style="margin: 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Order Number</p>
        <p style="margin: 4px 0 0 0; font-size: 20px; font-weight: 700; color: #1A1A1A;">{order_number}</p>
    </div>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 24px;">
        <tr>
            <td style="padding: 8px 0; font-size: 14px; color: #888888; width: 120px;">Customer</td>
            <td style="padding: 8px 0; font-size: 14px; color: #1A1A1A; font-weight: 600;">{customer_name}</td>
        </tr>
        <tr>
            <td style="padding: 8px 0; font-size: 14px; color: #888888;">Total</td>
            <td style="padding: 8px 0; font-size: 14px; color: #C6994A; font-weight: 600;">{_cents_to_dollars(total_cents)}</td>
        </tr>
    </table>

    <div style="text-align: center;">
        <a href="{settings.store_frontend_url}/admin/orders" style="display: inline-block; background-color: #1A1A1A; color: #FFFFFF; padding: 14px 32px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 4px; letter-spacing: 0.5px;">View Order</a>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": f"New Order - {order_number} ({customer_name})",
            "html": _base_email_template(content),
        })
        logger.info("New order alert sent to %s for order %s", to_email, order_number)
    except Exception:
        logger.exception("Failed to send new order alert to %s", to_email)


# ---------------------------------------------------------------------------
# Order Approved (STAFF -> SALESPERSON)
# ---------------------------------------------------------------------------

def send_order_approved(to_email: str, order_number: str) -> None:
    """Send a notification that an order has been approved by the purchasing team.

    Args:
        to_email: Recipient email address (salesperson).
        order_number: The order number.
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping order approved email to %s", to_email)
        return

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">Order Approved</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">Your order {order_number} has been approved by the purchasing team and is now confirmed.</p>

    <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
        <p style="margin: 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Order Number</p>
        <p style="margin: 4px 0 0 0; font-size: 20px; font-weight: 700; color: #1A1A1A;">{order_number}</p>
    </div>

    <div style="text-align: center; padding: 20px 0; margin-bottom: 20px;">
        <span style="display: inline-block; background-color: #2E7D32; color: #FFFFFF; padding: 8px 20px; font-size: 14px; font-weight: 600; border-radius: 20px; letter-spacing: 0.5px;">Approved</span>
    </div>

    <p style="margin: 0 0 24px 0; font-size: 15px; color: #1A1A1A; line-height: 1.6;">The order is now confirmed and will proceed to production. No further action is required from you.</p>

    <div style="text-align: center;">
        <a href="{settings.store_frontend_url}/admin/orders" style="display: inline-block; background-color: #1A1A1A; color: #FFFFFF; padding: 14px 32px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 4px; letter-spacing: 0.5px;">View Order</a>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": f"Order Approved - {order_number}",
            "html": _base_email_template(content),
        })
        logger.info("Order approved email sent to %s for order %s", to_email, order_number)
    except Exception:
        logger.exception("Failed to send order approved email to %s", to_email)


# ---------------------------------------------------------------------------
# Order Rejected (STAFF -> SALESPERSON)
# ---------------------------------------------------------------------------

def send_order_rejected(to_email: str, order_number: str, reason: str | None = None) -> None:
    """Send a notification that an order requires revisions before approval.

    Args:
        to_email: Recipient email address (salesperson).
        order_number: The order number.
        reason: Optional reason for rejection.
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping order rejected email to %s", to_email)
        return

    reason_section = ""
    if reason:
        reason_section = f"""
        <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
            <p style="margin: 0 0 4px 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Reason</p>
            <p style="margin: 4px 0 0 0; font-size: 14px; color: #1A1A1A; line-height: 1.6;">{reason}</p>
        </div>
        """

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">Order Needs Revision</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">Your order {order_number} requires revisions before it can be approved.</p>

    <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
        <p style="margin: 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Order Number</p>
        <p style="margin: 4px 0 0 0; font-size: 20px; font-weight: 700; color: #1A1A1A;">{order_number}</p>
    </div>

    {reason_section}

    <p style="margin: 0 0 24px 0; font-size: 15px; color: #1A1A1A; line-height: 1.6;">Please review the order and make the necessary changes, then resubmit for approval.</p>

    <div style="text-align: center;">
        <a href="{settings.store_frontend_url}/admin/orders" style="display: inline-block; background-color: #1A1A1A; color: #FFFFFF; padding: 14px 32px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 4px; letter-spacing: 0.5px;">Review Order</a>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": f"Order Needs Revision - {order_number}",
            "html": _base_email_template(content),
        })
        logger.info("Order rejected email sent to %s for order %s", to_email, order_number)
    except Exception:
        logger.exception("Failed to send order rejected email to %s", to_email)


# ---------------------------------------------------------------------------
# Mockup Ready (-> CUSTOMER)
# ---------------------------------------------------------------------------

def send_mockup_ready(
    to_email: str,
    first_name: str,
    order_number: str,
) -> None:
    """Notify a customer that their mockup is ready for review.

    Args:
        to_email: Customer's email address.
        first_name: The customer's first name.
        order_number: The order number.
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping mockup ready email to %s", to_email)
        return

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">Your Mockup is Ready</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">Hi {first_name}, the mockup for your order is ready for your review.</p>

    <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
        <p style="margin: 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Order Number</p>
        <p style="margin: 4px 0 0 0; font-size: 20px; font-weight: 700; color: #1A1A1A;">{order_number}</p>
    </div>

    <p style="margin: 0 0 24px 0; font-size: 15px; color: #1A1A1A; line-height: 1.6;">Please review the mockup and let us know if you'd like any changes or if you're ready to approve it and move to production.</p>

    <div style="text-align: center;">
        <a href="{settings.store_frontend_url}/account/orders" style="display: inline-block; background-color: #C6994A; color: #FFFFFF; padding: 14px 32px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 4px; letter-spacing: 0.5px;">Review Mockup</a>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": f"Mockup Ready for Review - {order_number}",
            "html": _base_email_template(content),
        })
        logger.info("Mockup ready email sent to %s for order %s", to_email, order_number)
    except Exception:
        logger.exception("Failed to send mockup ready email to %s", to_email)


# ---------------------------------------------------------------------------
# Mockup Response Alert (CUSTOMER -> STAFF)
# ---------------------------------------------------------------------------

def send_mockup_response_alert(
    to_email: str,
    order_number: str,
    approved: bool,
    feedback: str | None = None,
) -> None:
    """Send a staff notification about a customer's mockup response.

    Args:
        to_email: Staff recipient email address.
        order_number: The order number.
        approved: Whether the customer approved the mockup.
        feedback: Optional customer feedback.
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping mockup response alert to %s", to_email)
        return

    if approved:
        status_label = "Approved"
        status_color = "#2E7D32"
        action_text = "approved"
    else:
        status_label = "Revision Requested"
        status_color = "#E65100"
        action_text = "requested changes to"

    feedback_section = ""
    if feedback:
        feedback_section = f"""
        <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
            <p style="margin: 0 0 4px 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Customer Feedback</p>
            <p style="margin: 4px 0 0 0; font-size: 14px; color: #1A1A1A; line-height: 1.6;">{feedback}</p>
        </div>
        """

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">Mockup {status_label}</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">Customer has {action_text} the mockup for {order_number}.</p>

    <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 20px; border-radius: 0 4px 4px 0;">
        <p style="margin: 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Order Number</p>
        <p style="margin: 4px 0 0 0; font-size: 20px; font-weight: 700; color: #1A1A1A;">{order_number}</p>
    </div>

    <div style="text-align: center; padding: 20px 0; margin-bottom: 20px;">
        <span style="display: inline-block; background-color: {status_color}; color: #FFFFFF; padding: 8px 20px; font-size: 14px; font-weight: 600; border-radius: 20px; letter-spacing: 0.5px;">{status_label}</span>
    </div>

    {feedback_section}

    <div style="text-align: center;">
        <a href="{settings.store_frontend_url}/admin/orders" style="display: inline-block; background-color: #1A1A1A; color: #FFFFFF; padding: 14px 32px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 4px; letter-spacing: 0.5px;">View Order</a>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": f"Mockup {status_label} - {order_number}",
            "html": _base_email_template(content),
        })
        logger.info("Mockup response alert sent to %s for order %s (approved: %s)", to_email, order_number, approved)
    except Exception:
        logger.exception("Failed to send mockup response alert to %s", to_email)


# ---------------------------------------------------------------------------
# Sew-Out Ready (-> CUSTOMER)
# ---------------------------------------------------------------------------

def send_sewout_ready(to_email: str, first_name: str, order_number: str) -> None:
    """Send a notification that sew-out photos are ready for customer review.

    Args:
        to_email: Customer email address.
        first_name: The customer's first name.
        order_number: The order number.
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping sewout ready email to %s", to_email)
        return

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">Sew-Out Photos Ready</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">Hi {first_name}, the sew-out photos for order {order_number} are ready for your review.</p>

    <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
        <p style="margin: 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Order Number</p>
        <p style="margin: 4px 0 0 0; font-size: 20px; font-weight: 700; color: #1A1A1A;">{order_number}</p>
    </div>

    <p style="margin: 0 0 24px 0; font-size: 15px; color: #1A1A1A; line-height: 1.6;">We've completed a sample sew-out of your design. Please review the photos to make sure everything looks perfect before we proceed with full production.</p>

    <div style="text-align: center;">
        <a href="{settings.store_frontend_url}/account/mockups" style="display: inline-block; background-color: #1A1A1A; color: #FFFFFF; padding: 14px 32px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 4px; letter-spacing: 0.5px;">Review Sew-Out</a>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": f"Sew-Out Photos Ready - {order_number}",
            "html": _base_email_template(content),
        })
        logger.info("Sewout ready email sent to %s for order %s", to_email, order_number)
    except Exception:
        logger.exception("Failed to send sewout ready email to %s", to_email)


# ---------------------------------------------------------------------------
# Sew-Out Response Alert (CUSTOMER -> STAFF)
# ---------------------------------------------------------------------------

def send_sewout_response_alert(
    to_email: str,
    order_number: str,
    approved: bool,
    feedback: str | None = None,
) -> None:
    """Send a staff notification about a customer's sew-out response.

    Args:
        to_email: Staff recipient email address.
        order_number: The order number.
        approved: Whether the customer approved the sew-out.
        feedback: Optional customer feedback.
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping sewout response alert to %s", to_email)
        return

    if approved:
        status_label = "Approved"
        status_color = "#2E7D32"
        action_text = "approved"
    else:
        status_label = "Revision Requested"
        status_color = "#E65100"
        action_text = "requested changes to"

    feedback_section = ""
    if feedback:
        feedback_section = f"""
        <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
            <p style="margin: 0 0 4px 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Customer Feedback</p>
            <p style="margin: 4px 0 0 0; font-size: 14px; color: #1A1A1A; line-height: 1.6;">{feedback}</p>
        </div>
        """

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">Sew-Out {status_label}</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">Customer has {action_text} the sew-out for {order_number}.</p>

    <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 20px; border-radius: 0 4px 4px 0;">
        <p style="margin: 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Order Number</p>
        <p style="margin: 4px 0 0 0; font-size: 20px; font-weight: 700; color: #1A1A1A;">{order_number}</p>
    </div>

    <div style="text-align: center; padding: 20px 0; margin-bottom: 20px;">
        <span style="display: inline-block; background-color: {status_color}; color: #FFFFFF; padding: 8px 20px; font-size: 14px; font-weight: 600; border-radius: 20px; letter-spacing: 0.5px;">{status_label}</span>
    </div>

    {feedback_section}

    <div style="text-align: center;">
        <a href="{settings.store_frontend_url}/admin/orders" style="display: inline-block; background-color: #1A1A1A; color: #FFFFFF; padding: 14px 32px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 4px; letter-spacing: 0.5px;">View Order</a>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": f"Sew-Out {status_label} - {order_number}",
            "html": _base_email_template(content),
        })
        logger.info("Sewout response alert sent to %s for order %s (approved: %s)", to_email, order_number, approved)
    except Exception:
        logger.exception("Failed to send sewout response alert to %s", to_email)


# ---------------------------------------------------------------------------
# Contact Form Received (-> CUSTOMER)
# ---------------------------------------------------------------------------

def send_contact_form_received(to_email: str, first_name: str) -> None:
    """Send a confirmation that a contact form submission was received.

    Args:
        to_email: Customer email address.
        first_name: The customer's first name.
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping contact form received email to %s", to_email)
        return

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">We Received Your Message</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">Hi {first_name}, thanks for reaching out to King Cap.</p>

    <p style="margin: 0 0 16px 0; font-size: 15px; color: #1A1A1A; line-height: 1.6;">We've received your message and our team will review it shortly. You can expect a response within 1-2 business days.</p>

    <p style="margin: 0 0 24px 0; font-size: 15px; color: #1A1A1A; line-height: 1.6;">If your matter is urgent, please don't hesitate to contact us directly at <a href="mailto:info@wearkingcap.com" style="color: #C6994A; text-decoration: none; font-weight: 600;">info@wearkingcap.com</a></p>

    <p style="margin: 0; font-size: 14px; color: #888888;">Thank you for your interest in King Cap.</p>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": "We Received Your Message - King Cap",
            "html": _base_email_template(content),
        })
        logger.info("Contact form received email sent to %s", to_email)
    except Exception:
        logger.exception("Failed to send contact form received email to %s", to_email)


# ---------------------------------------------------------------------------
# Contact Form Alert (-> STAFF)
# ---------------------------------------------------------------------------

def send_contact_form_alert(
    to_email: str,
    name: str,
    email: str,
    message: str,
) -> None:
    """Forward a contact form submission to staff.

    Args:
        to_email: Staff recipient email address.
        name: The visitor's full name.
        email: The visitor's email address.
        message: The message content.
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping contact form alert to %s", to_email)
        return

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">New Contact Form Submission</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">A new message has been submitted through the contact form.</p>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 24px;">
        <tr>
            <td style="padding: 8px 0; font-size: 14px; color: #888888; width: 120px;">Name</td>
            <td style="padding: 8px 0; font-size: 14px; color: #1A1A1A; font-weight: 600;">{name}</td>
        </tr>
        <tr>
            <td style="padding: 8px 0; font-size: 14px; color: #888888;">Email</td>
            <td style="padding: 8px 0; font-size: 14px; color: #1A1A1A;">
                <a href="mailto:{email}" style="color: #C6994A; text-decoration: none;">{email}</a>
            </td>
        </tr>
    </table>

    <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
        <p style="margin: 0 0 4px 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Message</p>
        <p style="margin: 4px 0 0 0; font-size: 14px; color: #1A1A1A; line-height: 1.6; white-space: pre-wrap;">{message}</p>
    </div>

    <p style="margin: 0; font-size: 14px; color: #666666;">Reply directly to this person at <a href="mailto:{email}" style="color: #C6994A; text-decoration: none;">{email}</a>.</p>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": f"Contact Form - {name}",
            "html": _base_email_template(content),
        })
        logger.info("Contact form alert sent to %s from %s", to_email, email)
    except Exception:
        logger.exception("Failed to send contact form alert to %s", to_email)


# ---------------------------------------------------------------------------
# Design Request Alert (-> DESIGN MANAGER)
# ---------------------------------------------------------------------------

def send_design_request_alert(
    to_email: str,
    request_number: str,
    customer_name: str,
    details: str | None = None,
) -> None:
    """Notify the design manager of a new design request.

    Args:
        to_email: Design manager's email address.
        request_number: The design request number.
        customer_name: The customer's full name.
        details: Optional design request details.
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping design request alert to %s", to_email)
        return

    details_section = ""
    if details:
        details_section = f"""
        <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin: 20px 0; border-radius: 0 4px 4px 0;">
            <p style="margin: 0 0 4px 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Details</p>
            <p style="margin: 0; font-size: 14px; color: #1A1A1A; line-height: 1.6;">{details}</p>
        </div>
        """

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">New Design Request</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">A new design request has been submitted and is awaiting your review.</p>

    <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
        <p style="margin: 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Request Number</p>
        <p style="margin: 4px 0 0 0; font-size: 20px; font-weight: 700; color: #1A1A1A;">{request_number}</p>
    </div>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 24px;">
        <tr>
            <td style="padding: 8px 0; font-size: 14px; color: #888888; width: 120px;">Customer</td>
            <td style="padding: 8px 0; font-size: 14px; color: #1A1A1A; font-weight: 600;">{customer_name}</td>
        </tr>
    </table>

    {details_section}

    <div style="text-align: center;">
        <a href="{settings.store_frontend_url}/admin/designs" style="display: inline-block; background-color: #1A1A1A; color: #FFFFFF; padding: 14px 32px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 4px; letter-spacing: 0.5px;">Review Request</a>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": f"New Design Request - {request_number} ({customer_name})",
            "html": _base_email_template(content),
        })
        logger.info("Design request alert sent to %s for request %s", to_email, request_number)
    except Exception:
        logger.exception("Failed to send design request alert to %s", to_email)


# ---------------------------------------------------------------------------
# Design Ready for Review (-> CUSTOMER + SALESPERSON)
# ---------------------------------------------------------------------------

def send_design_ready_for_review(to_email: str, first_name: str, request_number: str) -> None:
    """Send a notification that a design is ready for review.

    Args:
        to_email: Recipient email address (customer or salesperson).
        first_name: The recipient's first name.
        request_number: The design request number.
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping design ready email to %s", to_email)
        return

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">Design Ready for Review</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">Hi {first_name}, your design is ready for review.</p>

    <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
        <p style="margin: 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Request Number</p>
        <p style="margin: 4px 0 0 0; font-size: 20px; font-weight: 700; color: #1A1A1A;">{request_number}</p>
    </div>

    <p style="margin: 0 0 24px 0; font-size: 15px; color: #1A1A1A; line-height: 1.6;">Our design team has completed your design and it's ready for your review. Please take a look and let us know if it meets your expectations or if you'd like any adjustments.</p>

    <div style="text-align: center;">
        <a href="{settings.store_frontend_url}/account/designs" style="display: inline-block; background-color: #1A1A1A; color: #FFFFFF; padding: 14px 32px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 4px; letter-spacing: 0.5px;">Review Design</a>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": f"Design Ready for Review - {request_number}",
            "html": _base_email_template(content),
        })
        logger.info("Design ready email sent to %s for request %s", to_email, request_number)
    except Exception:
        logger.exception("Failed to send design ready email to %s", to_email)


# ---------------------------------------------------------------------------
# Design Feedback Alert (-> DESIGN MANAGER)
# ---------------------------------------------------------------------------

def send_design_feedback_alert(
    to_email: str,
    request_number: str,
    feedback: str | None = None,
) -> None:
    """Notify the design manager of feedback on a design.

    Args:
        to_email: Design manager's email address.
        request_number: The design request number.
        feedback: Optional feedback text.
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping design feedback alert to %s", to_email)
        return

    feedback_section = ""
    if feedback:
        feedback_section = f"""
        <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin: 20px 0; border-radius: 0 4px 4px 0;">
            <p style="margin: 0 0 4px 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Feedback</p>
            <p style="margin: 0; font-size: 14px; color: #1A1A1A; line-height: 1.6;">{feedback}</p>
        </div>
        """

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">Design Feedback Received</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">Feedback has been submitted for design request {request_number}.</p>

    <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
        <p style="margin: 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Request Number</p>
        <p style="margin: 4px 0 0 0; font-size: 20px; font-weight: 700; color: #1A1A1A;">{request_number}</p>
    </div>

    {feedback_section}

    <div style="text-align: center;">
        <a href="{settings.store_frontend_url}/admin/designs" style="display: inline-block; background-color: #1A1A1A; color: #FFFFFF; padding: 14px 32px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 4px; letter-spacing: 0.5px;">View Request</a>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": f"Design Revision Requested - {request_number}",
            "html": _base_email_template(content),
        })
        logger.info("Design feedback alert sent to %s for request %s", to_email, request_number)
    except Exception:
        logger.exception("Failed to send design feedback alert to %s", to_email)


# ---------------------------------------------------------------------------
# Quote to Customer
# ---------------------------------------------------------------------------

def send_quote_to_customer(
    to_email: str,
    first_name: str,
    quote_number: str,
    total_cents: int,
    valid_until: str,
    accept_url: str,
) -> None:
    """Send a quote to a customer for review and acceptance.

    Args:
        to_email: Customer email address.
        first_name: The customer's first name.
        quote_number: The quote number.
        total_cents: Quote total in cents.
        valid_until: Human-readable date the quote expires (e.g. "March 15, 2026").
        accept_url: URL where the customer can view and accept the quote.
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping quote email to %s", to_email)
        return

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">Your Quote from King Cap</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">Hi {first_name}, here's the quote you requested.</p>

    <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
        <p style="margin: 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Quote Number</p>
        <p style="margin: 4px 0 0 0; font-size: 20px; font-weight: 700; color: #1A1A1A;">{quote_number}</p>
    </div>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 24px;">
        <tr>
            <td style="padding: 8px 0; font-size: 14px; color: #888888; width: 140px;">Total</td>
            <td style="padding: 8px 0; font-size: 16px; color: #C6994A; font-weight: 700;">{_cents_to_dollars(total_cents)}</td>
        </tr>
        <tr>
            <td style="padding: 8px 0; font-size: 14px; color: #888888;">Valid Until</td>
            <td style="padding: 8px 0; font-size: 14px; color: #1A1A1A; font-weight: 600;">{valid_until}</td>
        </tr>
    </table>

    <p style="margin: 0 0 28px 0; font-size: 15px; color: #1A1A1A; line-height: 1.6;">Click below to view the full quote details and accept it to proceed with your order.</p>

    <div style="text-align: center; margin-bottom: 24px;">
        <a href="{accept_url}" style="display: inline-block; background-color: #1A1A1A; color: #FFFFFF; padding: 14px 32px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 4px; letter-spacing: 0.5px;">View &amp; Accept Quote</a>
    </div>

    <p style="margin: 0; font-size: 13px; color: #888888;">If you have any questions about this quote, please contact your sales representative or email us at <a href="mailto:info@wearkingcap.com" style="color: #C6994A; text-decoration: none;">info@wearkingcap.com</a></p>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": f"Quote from King Cap - {quote_number}",
            "html": _base_email_template(content),
        })
        logger.info("Quote email sent to %s for quote %s", to_email, quote_number)
    except Exception:
        logger.exception("Failed to send quote email to %s", to_email)


# ---------------------------------------------------------------------------
# Quote Response Alert (-> SALESPERSON)
# ---------------------------------------------------------------------------

def send_quote_response_alert(
    to_email: str,
    quote_number: str,
    accepted: bool,
    reason: str | None = None,
) -> None:
    """Send a salesperson notification about a customer's quote response.

    Args:
        to_email: Salesperson email address.
        quote_number: The quote number.
        accepted: Whether the customer accepted or declined the quote.
        reason: Optional reason (typically for declined quotes).
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping quote response alert to %s", to_email)
        return

    if accepted:
        status_label = "Accepted"
        status_color = "#2E7D32"
        intro = f"The customer has accepted quote {quote_number}. The order is ready to proceed."
    else:
        status_label = "Declined"
        status_color = "#C62828"
        intro = f"The customer has declined quote {quote_number}."

    reason_section = ""
    if reason:
        reason_section = f"""
        <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
            <p style="margin: 0 0 4px 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Reason</p>
            <p style="margin: 4px 0 0 0; font-size: 14px; color: #1A1A1A; line-height: 1.6;">{reason}</p>
        </div>
        """

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">Quote {status_label}</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">{intro}</p>

    <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 20px; border-radius: 0 4px 4px 0;">
        <p style="margin: 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Quote Number</p>
        <p style="margin: 4px 0 0 0; font-size: 20px; font-weight: 700; color: #1A1A1A;">{quote_number}</p>
    </div>

    <div style="text-align: center; padding: 20px 0; margin-bottom: 20px;">
        <span style="display: inline-block; background-color: {status_color}; color: #FFFFFF; padding: 8px 20px; font-size: 14px; font-weight: 600; border-radius: 20px; letter-spacing: 0.5px;">{status_label}</span>
    </div>

    {reason_section}

    <div style="text-align: center;">
        <a href="{settings.store_frontend_url}/admin/quotes" style="display: inline-block; background-color: #1A1A1A; color: #FFFFFF; padding: 14px 32px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 4px; letter-spacing: 0.5px;">View Quote</a>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": f"Quote {status_label} - {quote_number}",
            "html": _base_email_template(content),
        })
        logger.info("Quote response alert sent to %s for quote %s (accepted: %s)", to_email, quote_number, accepted)
    except Exception:
        logger.exception("Failed to send quote response alert to %s", to_email)


# ---------------------------------------------------------------------------
# Return Request Received (-> CUSTOMER)
# ---------------------------------------------------------------------------

def send_return_request_received(to_email: str, first_name: str, return_number: str) -> None:
    """Send a confirmation that a return request was received.

    Args:
        to_email: Customer email address.
        first_name: The customer's first name.
        return_number: The return request number.
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping return request received email to %s", to_email)
        return

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">Return Request Received</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">Hi {first_name}, we've received your return request.</p>

    <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
        <p style="margin: 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Return Number</p>
        <p style="margin: 4px 0 0 0; font-size: 20px; font-weight: 700; color: #1A1A1A;">{return_number}</p>
    </div>

    <p style="margin: 0 0 16px 0; font-size: 15px; color: #1A1A1A; line-height: 1.6;">Our team is reviewing your return request and will get back to you within 1-2 business days with next steps.</p>

    <p style="margin: 0 0 24px 0; font-size: 15px; color: #1A1A1A; line-height: 1.6;">You can check the status of your return at any time in your account.</p>

    <div style="text-align: center;">
        <a href="{settings.store_frontend_url}/account/orders" style="display: inline-block; background-color: #1A1A1A; color: #FFFFFF; padding: 14px 32px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 4px; letter-spacing: 0.5px;">View Your Orders</a>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": f"Return Request Received - {return_number}",
            "html": _base_email_template(content),
        })
        logger.info("Return request received email sent to %s for return %s", to_email, return_number)
    except Exception:
        logger.exception("Failed to send return request received email to %s", to_email)


# ---------------------------------------------------------------------------
# Return Request Alert (-> STAFF)
# ---------------------------------------------------------------------------

def send_return_request_alert(
    to_email: str,
    return_number: str,
    customer_name: str,
    reason: str | None = None,
) -> None:
    """Notify staff about a new return request.

    Args:
        to_email: Staff member's email address.
        return_number: The return request number.
        customer_name: The customer's full name.
        reason: Optional reason for the return.
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping return request alert to %s", to_email)
        return

    reason_section = ""
    if reason:
        reason_section = f"""
        <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin: 20px 0; border-radius: 0 4px 4px 0;">
            <p style="margin: 0 0 4px 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Reason</p>
            <p style="margin: 0; font-size: 14px; color: #1A1A1A; line-height: 1.6;">{reason}</p>
        </div>
        """

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">New Return Request</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">A new return request has been submitted and needs review.</p>

    <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
        <p style="margin: 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Return Number</p>
        <p style="margin: 4px 0 0 0; font-size: 20px; font-weight: 700; color: #1A1A1A;">{return_number}</p>
    </div>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 24px;">
        <tr>
            <td style="padding: 8px 0; font-size: 14px; color: #888888; width: 120px;">Customer</td>
            <td style="padding: 8px 0; font-size: 14px; color: #1A1A1A; font-weight: 600;">{customer_name}</td>
        </tr>
    </table>

    {reason_section}

    <div style="text-align: center;">
        <a href="{settings.store_frontend_url}/admin/returns" style="display: inline-block; background-color: #1A1A1A; color: #FFFFFF; padding: 14px 32px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 4px; letter-spacing: 0.5px;">Review Return</a>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": f"New Return Request - {return_number} ({customer_name})",
            "html": _base_email_template(content),
        })
        logger.info("Return request alert sent to %s for return %s", to_email, return_number)
    except Exception:
        logger.exception("Failed to send return request alert to %s", to_email)


# ---------------------------------------------------------------------------
# Return Approved (-> CUSTOMER)
# ---------------------------------------------------------------------------

def send_return_approved(
    to_email: str,
    first_name: str,
    return_number: str,
    instructions: str | None = None,
) -> None:
    """Send a notification that a return request has been approved.

    Args:
        to_email: Customer email address.
        first_name: The customer's first name.
        return_number: The return request number.
        instructions: Optional return shipping instructions.
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping return approved email to %s", to_email)
        return

    instructions_section = ""
    if instructions:
        instructions_section = f"""
        <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
            <p style="margin: 0 0 4px 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Return Instructions</p>
            <p style="margin: 4px 0 0 0; font-size: 14px; color: #1A1A1A; line-height: 1.6; white-space: pre-wrap;">{instructions}</p>
        </div>
        """

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">Return Approved</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">Hi {first_name}, your return request has been approved.</p>

    <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
        <p style="margin: 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Return Number</p>
        <p style="margin: 4px 0 0 0; font-size: 20px; font-weight: 700; color: #1A1A1A;">{return_number}</p>
    </div>

    <div style="text-align: center; padding: 20px 0; margin-bottom: 20px;">
        <span style="display: inline-block; background-color: #2E7D32; color: #FFFFFF; padding: 8px 20px; font-size: 14px; font-weight: 600; border-radius: 20px; letter-spacing: 0.5px;">Approved</span>
    </div>

    {instructions_section}

    <p style="margin: 0 0 24px 0; font-size: 15px; color: #1A1A1A; line-height: 1.6;">Once we receive your return, we'll process your refund within 5-7 business days. You'll receive a confirmation email when the refund has been issued.</p>

    <p style="margin: 0; font-size: 14px; color: #888888;">If you have any questions, contact us at <a href="mailto:info@wearkingcap.com" style="color: #C6994A; text-decoration: none;">info@wearkingcap.com</a></p>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": f"Return Approved - {return_number}",
            "html": _base_email_template(content),
        })
        logger.info("Return approved email sent to %s for return %s", to_email, return_number)
    except Exception:
        logger.exception("Failed to send return approved email to %s", to_email)


# ---------------------------------------------------------------------------
# Return Rejected (-> CUSTOMER)
# ---------------------------------------------------------------------------

def send_return_rejected(
    to_email: str,
    first_name: str,
    return_number: str,
    reason: str | None = None,
) -> None:
    """Send a notification that a return request was not approved.

    Args:
        to_email: Customer email address.
        first_name: The customer's first name.
        return_number: The return request number.
        reason: Optional reason the return was not approved.
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping return rejected email to %s", to_email)
        return

    reason_section = ""
    if reason:
        reason_section = f"""
        <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
            <p style="margin: 0 0 4px 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Reason</p>
            <p style="margin: 4px 0 0 0; font-size: 14px; color: #1A1A1A; line-height: 1.6;">{reason}</p>
        </div>
        """

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">Return Update</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">Hi {first_name}, we've reviewed your return request.</p>

    <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
        <p style="margin: 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Return Number</p>
        <p style="margin: 4px 0 0 0; font-size: 20px; font-weight: 700; color: #1A1A1A;">{return_number}</p>
    </div>

    <p style="margin: 0 0 24px 0; font-size: 15px; color: #1A1A1A; line-height: 1.6;">Unfortunately, we're unable to approve your return request at this time.</p>

    {reason_section}

    <p style="margin: 0; font-size: 14px; color: #888888;">If you have questions or believe this was an error, please contact us at <a href="mailto:info@wearkingcap.com" style="color: #C6994A; text-decoration: none;">info@wearkingcap.com</a></p>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": f"Return Update - {return_number}",
            "html": _base_email_template(content),
        })
        logger.info("Return rejected email sent to %s for return %s", to_email, return_number)
    except Exception:
        logger.exception("Failed to send return rejected email to %s", to_email)


# ---------------------------------------------------------------------------
# Refund Processed (-> CUSTOMER)
# ---------------------------------------------------------------------------

def send_refund_processed(
    to_email: str,
    first_name: str,
    return_number: str,
    amount_cents: int,
) -> None:
    """Notify a customer that their refund has been processed.

    Args:
        to_email: Customer's email address.
        first_name: The customer's first name.
        return_number: The return request number.
        amount_cents: Refund amount in cents.
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping refund processed email to %s", to_email)
        return

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">Refund Processed</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">Hi {first_name}, your refund has been processed.</p>

    <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
        <p style="margin: 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Return Number</p>
        <p style="margin: 4px 0 0 0; font-size: 20px; font-weight: 700; color: #1A1A1A;">{return_number}</p>
    </div>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 24px;">
        <tr>
            <td style="padding: 12px 0 0 0; font-size: 16px; font-weight: 700; color: #1A1A1A;">Refund Amount</td>
            <td style="padding: 12px 0 0 0; font-size: 16px; font-weight: 700; color: #C6994A; text-align: right;">{_cents_to_dollars(amount_cents)}</td>
        </tr>
    </table>

    <p style="margin: 0 0 16px 0; font-size: 15px; color: #1A1A1A; line-height: 1.6;">The refund has been issued to your original payment method. Please allow 5-10 business days for the amount to appear on your statement.</p>

    <p style="margin: 0; font-size: 14px; color: #888888;">If you have any questions, feel free to reply to this email.</p>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": f"Refund Processed - {return_number}",
            "html": _base_email_template(content),
        })
        logger.info("Refund processed email sent to %s for return %s", to_email, return_number)
    except Exception:
        logger.exception("Failed to send refund processed email to %s", to_email)


# ---------------------------------------------------------------------------
# Sample Request Alert (-> STAFF / PM)
# ---------------------------------------------------------------------------

def send_sample_request_alert(
    to_email: str,
    sample_number: str,
    customer_name: str,
    details: str | None = None,
) -> None:
    """Notify the PM of a new sample request needing approval.

    Args:
        to_email: PM's email address.
        sample_number: The sample request number.
        customer_name: The customer's full name.
        details: Optional details about the sample request.
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping sample request alert to %s", to_email)
        return

    details_section = ""
    if details:
        details_section = f"""
        <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin: 20px 0; border-radius: 0 4px 4px 0;">
            <p style="margin: 0 0 4px 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Details</p>
            <p style="margin: 0; font-size: 14px; color: #1A1A1A; line-height: 1.6;">{details}</p>
        </div>
        """

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">New Sample Request</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">A new sample request has been submitted and needs your approval.</p>

    <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
        <p style="margin: 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Sample Number</p>
        <p style="margin: 4px 0 0 0; font-size: 20px; font-weight: 700; color: #1A1A1A;">{sample_number}</p>
    </div>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 24px;">
        <tr>
            <td style="padding: 8px 0; font-size: 14px; color: #888888; width: 120px;">Customer</td>
            <td style="padding: 8px 0; font-size: 14px; color: #1A1A1A; font-weight: 600;">{customer_name}</td>
        </tr>
    </table>

    {details_section}

    <div style="text-align: center;">
        <a href="{settings.store_frontend_url}/admin/samples" style="display: inline-block; background-color: #1A1A1A; color: #FFFFFF; padding: 14px 32px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 4px; letter-spacing: 0.5px;">Review Sample Request</a>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": f"New Sample Request - {sample_number} ({customer_name})",
            "html": _base_email_template(content),
        })
        logger.info("Sample request alert sent to %s for sample %s", to_email, sample_number)
    except Exception:
        logger.exception("Failed to send sample request alert to %s", to_email)


# ---------------------------------------------------------------------------
# Sample Approved Alert (-> SALESPERSON)
# ---------------------------------------------------------------------------

def send_sample_approved_alert(to_email: str, sample_number: str) -> None:
    """Send a salesperson notification that a sample request has been approved.

    Args:
        to_email: Salesperson email address.
        sample_number: The sample request number.
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping sample approved alert to %s", to_email)
        return

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">Sample Request Approved</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">Your sample request has been approved and is ready to proceed.</p>

    <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
        <p style="margin: 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Sample Number</p>
        <p style="margin: 4px 0 0 0; font-size: 20px; font-weight: 700; color: #1A1A1A;">{sample_number}</p>
    </div>

    <div style="text-align: center; padding: 20px 0; margin-bottom: 20px;">
        <span style="display: inline-block; background-color: #2E7D32; color: #FFFFFF; padding: 8px 20px; font-size: 14px; font-weight: 600; border-radius: 20px; letter-spacing: 0.5px;">Approved</span>
    </div>

    <p style="margin: 0 0 24px 0; font-size: 15px; color: #1A1A1A; line-height: 1.6;">The sample has been approved and will be prepared for shipping. You'll be notified when it's on its way.</p>

    <div style="text-align: center;">
        <a href="{settings.store_frontend_url}/admin/samples" style="display: inline-block; background-color: #1A1A1A; color: #FFFFFF; padding: 14px 32px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 4px; letter-spacing: 0.5px;">View Sample</a>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": f"Sample Approved - {sample_number}",
            "html": _base_email_template(content),
        })
        logger.info("Sample approved alert sent to %s for sample %s", to_email, sample_number)
    except Exception:
        logger.exception("Failed to send sample approved alert to %s", to_email)


# ---------------------------------------------------------------------------
# Sample Rejected Alert (-> SALESPERSON)
# ---------------------------------------------------------------------------

def send_sample_rejected_alert(to_email: str, sample_number: str, reason: str | None = None) -> None:
    """Send a salesperson notification that a sample request has been rejected.

    Args:
        to_email: Salesperson email address.
        sample_number: The sample request number.
        reason: Optional reason for rejection.
    """
    if not settings.resend_api_key:
        logger.info("Resend API key not configured -- skipping sample rejected alert to %s", to_email)
        return

    reason_section = ""
    if reason:
        reason_section = f"""
        <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
            <p style="margin: 0 0 4px 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Reason</p>
            <p style="margin: 4px 0 0 0; font-size: 14px; color: #1A1A1A; line-height: 1.6;">{reason}</p>
        </div>
        """

    content = f"""
    <h2 style="margin: 0 0 8px 0; font-size: 22px; color: #1A1A1A;">Sample Request Not Approved</h2>
    <p style="margin: 0 0 24px 0; font-size: 15px; color: #666666;">Your sample request {sample_number} was not approved.</p>

    <div style="background-color: #FAF6F0; border-left: 4px solid #C6994A; padding: 16px 20px; margin-bottom: 24px; border-radius: 0 4px 4px 0;">
        <p style="margin: 0; font-size: 13px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Sample Number</p>
        <p style="margin: 4px 0 0 0; font-size: 20px; font-weight: 700; color: #1A1A1A;">{sample_number}</p>
    </div>

    {reason_section}

    <p style="margin: 0 0 24px 0; font-size: 15px; color: #1A1A1A; line-height: 1.6;">Please review the feedback and make any necessary adjustments before resubmitting. If you have questions, contact your manager.</p>

    <div style="text-align: center;">
        <a href="{settings.store_frontend_url}/admin/samples" style="display: inline-block; background-color: #1A1A1A; color: #FFFFFF; padding: 14px 32px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 4px; letter-spacing: 0.5px;">View Sample</a>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": f"Sample Not Approved - {sample_number}",
            "html": _base_email_template(content),
        })
        logger.info("Sample rejected alert sent to %s for sample %s", to_email, sample_number)
    except Exception:
        logger.exception("Failed to send sample rejected alert to %s", to_email)
