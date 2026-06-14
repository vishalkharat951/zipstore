import base64
import io
import logging
import uuid

import qrcode

logger = logging.getLogger(__name__)

UPI_ID = '8669303401@ybl'
MERCHANT_NAME = 'Zip Store'
CURRENCY = 'INR'


def generate_upi_intent_url(amount, order_id, transaction_ref):
    tn = f'Order {order_id}'
    upi_url = (
        f'upi://pay?pa={UPI_ID}'
        f'&pn={MERCHANT_NAME}'
        f'&am={amount:.2f}'
        f'&tn={tn}'
        f'&tr={transaction_ref}'
        f'&cu={CURRENCY}'
    )
    return upi_url


def generate_qr_base64(upi_url, box_size=8, border=2):
    qr = qrcode.QRCode(box_size=box_size, border=border)
    qr.add_data(upi_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f'data:image/png;base64,{b64}'


def generate_transaction_ref(order):
    return f'UPI-{order.order_id}-{uuid.uuid4().hex[:6].upper()}'
