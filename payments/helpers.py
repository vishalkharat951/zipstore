import base64
import hashlib
import json
import logging
import uuid

import requests

from .models import PaymentTransaction, PhonePeSettings

logger = logging.getLogger(__name__)


class PhonePeError(Exception):
    pass


class ConfigError(PhonePeError):
    pass


class PaymentError(PhonePeError):
    pass


class VerificationError(PhonePeError):
    pass


def get_config():
    config = PhonePeSettings.get_active()
    if not config:
        raise ConfigError('PhonePe is not configured. Add settings in admin.')
    return config


def get_base_url():
    config = get_config()
    if config.environment == 'production':
        return 'https://api.phonepe.com/apis/hermes'
    return 'https://api-preprod.phonepe.com/apis/pg-sandbox'


def generate_transaction_id(order):
    return f'TXN-{order.order_id}-{uuid.uuid4().hex[:6].upper()}'


def create_payload(order, transaction_id, redirect_url, callback_url, mobile_number):
    config = get_config()
    amount_paise = int(order.total_amount * 100)
    return {
        'merchantId': config.merchant_id,
        'merchantTransactionId': transaction_id,
        'merchantUserId': str(order.user.id),
        'amount': amount_paise,
        'redirectUrl': redirect_url,
        'redirectMode': 'POST',
        'callbackUrl': callback_url,
        'mobileNumber': mobile_number,
        'paymentInstrument': {
            'type': 'PAY_PAGE',
        },
    }


def generate_checksum(payload, endpoint):
    config = get_config()
    payload_str = json.dumps(payload, separators=(',', ':')) if isinstance(payload, dict) else payload
    base64_str = base64.b64encode(payload_str.encode()).decode()
    string_to_hash = base64_str + endpoint + config.salt_key
    sha256_hash = hashlib.sha256(string_to_hash.encode()).hexdigest()
    return f'{sha256_hash}###{config.salt_index}', base64_str


def initiate_payment(order, request):
    config = get_config()
    transaction_id = generate_transaction_id(order)
    mobile_number = order.mobile_number
    redirect_url = request.build_absolute_uri('/payments/redirect/')
    callback_url = config.callback_url or request.build_absolute_uri('/payments/callback/')

    payload = create_payload(order, transaction_id, redirect_url, callback_url, mobile_number)
    endpoint = '/pg/v1/pay'
    checksum, base64_payload = generate_checksum(payload, endpoint)
    url = get_base_url() + endpoint

    headers = {
        'Content-Type': 'application/json',
        'X-VERIFY': checksum,
    }

    body = {'request': base64_payload}

    PaymentTransaction.objects.create(
        order=order,
        transaction_id=transaction_id,
        payment_status=PaymentTransaction.PaymentStatus.PENDING,
        response_data={'payload': payload},
    )

    try:
        response = requests.post(url, json=body, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        PaymentTransaction.objects.filter(transaction_id=transaction_id).update(
            response_data=data,
        )

        if data.get('success') and data.get('code') == 'PAYMENT_INITIATED':
            redirect_url = (
                data.get('data', {})
                .get('instrumentResponse', {})
                .get('redirectInfo', {})
                .get('url')
            )
            if not redirect_url:
                raise PaymentError('PhonePe did not return a redirect URL.')
            return redirect_url, transaction_id
        else:
            error_msg = data.get('message', 'Payment initiation failed.')
            raise PaymentError(error_msg)

    except requests.RequestException as e:
        PaymentTransaction.objects.filter(transaction_id=transaction_id).update(
            payment_status=PaymentTransaction.PaymentStatus.FAILED,
            response_data={'error': str(e)},
        )
        raise PaymentError(f'PhonePe API request failed: {e}')


def verify_callback(response_data, x_verify_header):
    config = get_config()

    if not response_data or not x_verify_header:
        raise VerificationError('Missing callback response or X-VERIFY header.')

    decoded = base64.b64decode(response_data).decode()
    callback_json = json.loads(decoded)

    merchant_transaction_id = callback_json.get('data', {}).get('merchantTransactionId')
    if not merchant_transaction_id:
        raise VerificationError('merchantTransactionId not found in callback.')

    endpoint = f'/pg/v1/status/{config.merchant_id}/{merchant_transaction_id}'
    string_to_hash = response_data + endpoint + config.salt_key
    expected_hash = hashlib.sha256(string_to_hash.encode()).hexdigest()
    expected_checksum = f'{expected_hash}###{config.salt_index}'

    if expected_checksum != x_verify_header:
        raise VerificationError('Callback checksum verification failed.')

    return callback_json


def check_payment_status(transaction_id):
    config = get_config()
    endpoint = f'/pg/v1/status/{config.merchant_id}/{transaction_id}'
    url = get_base_url() + endpoint

    checksum, _ = generate_checksum('', endpoint)
    headers = {
        'Content-Type': 'application/json',
        'X-VERIFY': checksum,
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f'PhonePe status check failed: {e}')
        return None
