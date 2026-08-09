const crypto = require('crypto');
const PaymentTransaction = require('../models/PaymentTransaction');
const Order = require('../models/Order');

const BASE_URLS = {
  test: 'https://api-preprod.phonepe.com/apis/hermes',
  production: 'https://api.phonepe.com/apis/hermes',
};

const PAY = '/pg/v1/pay';
const STATUS_PREFIX = '/pg/v1/status/';
const REFUND = '/pg/v1/refund';
const DEFAULT_TIMEOUT_MS = 30000;

class PhonePeError extends Error {
  constructor(message, code = 'PHONEPE_ERROR') {
    super(message);
    this.code = code;
  }
}

class PhonePeConfigError extends PhonePeError {
  constructor(message) {
    super(message, 'PHONEPE_CONFIG_ERROR');
  }
}

class PhonePeSignatureError extends PhonePeError {
  constructor(message) {
    super(message, 'PHONEPE_SIGNATURE_ERROR');
  }
}

function getConfig() {
  const environment = (process.env.PHONEPE_ENV || 'test').toLowerCase();
  const isProduction = environment === 'production';

  const merchantId = process.env.PHONEPE_MERCHANT_ID;
  const saltKey = process.env.PHONEPE_SALT_KEY;
  const saltIndex = process.env.PHONEPE_SALT_INDEX || '1';

  if (!merchantId || !saltKey) {
    throw new PhonePeConfigError(
      'PhonePe is not configured. Set PHONEPE_MERCHANT_ID and PHONEPE_SALT_KEY environment variables.'
    );
  }

  if (isProduction) {
    if (!process.env.PHONEPE_CALLBACK_URL) {
      throw new PhonePeConfigError('PHONEPE_CALLBACK_URL must be set for production.');
    }
  }

  return {
    merchantId,
    saltKey,
    saltIndex,
    environment,
    isProduction,
    baseUrl: isProduction ? BASE_URLS.production : BASE_URLS.test,
    callbackUrl:
      process.env.PHONEPE_CALLBACK_URL || `${process.env.API_URL || ''}/api/payments/phonepe-callback`,
    redirectUrl:
      process.env.PHONEPE_REDIRECT_URL ||
      `${process.env.FRONTEND_URL || ''}/my-orders.html`,
  };
}

function generateTransactionId() {
  const ts = Date.now();
  const rand = crypto.randomBytes(4).toString('hex').toUpperCase();
  return `TXN_${ts}_${rand}`;
}

function buildXVerify(payloadBase64, endpoint, saltKey, saltIndex) {
  const hash = crypto.createHash('sha256').update(payloadBase64 + endpoint + saltKey).digest('hex');
  return `${hash}###${saltIndex}`;
}

function safeEqual(a, b) {
  const ba = Buffer.from(String(a));
  const bb = Buffer.from(String(b));
  if (ba.length !== bb.length) return false;
  return crypto.timingSafeEqual(ba, bb);
}

function amountToPaise(amount) {
  return Math.round(Number(amount) * 100);
}

function createPayload({ order, transactionId, config, mobileNumber, redirectUrl }) {
  return {
    merchantId: config.merchantId,
    merchantTransactionId: transactionId,
    merchantUserId: 'MUID_' + String(order.userId || 'guest'),
    amount: amountToPaise(order.totalAmount),
    redirectUrl: redirectUrl || config.redirectUrl,
    redirectMode: 'POST',
    callbackUrl: config.callbackUrl,
    mobileNumber: mobileNumber || '',
    paymentInstrument: { type: 'PAY_PAGE' },
  };
}

async function initiatePayment({ order, mobileNumber, redirectUrl }) {
  const config = getConfig();
  const transactionId = generateTransactionId();

  const payload = createPayload({ order, transactionId, config, mobileNumber, redirectUrl });
  const payloadJson = JSON.stringify(payload);
  const payloadBase64 = Buffer.from(payloadJson, 'utf-8').toString('base64');
  const xVerify = buildXVerify(payloadBase64, PAY, config.saltKey, config.saltIndex);

  let transaction = await PaymentTransaction.findOne({ order: order._id, paymentStatus: 'pending' });

  if (!transaction) {
    transaction = await PaymentTransaction.create({
      order: order._id,
      transactionId,
      paymentMethod: 'phonepe',
      paymentStatus: 'pending',
      amount: order.totalAmount,
      requestPayload: payload,
    });
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);

  try {
    const res = await fetch(config.baseUrl + PAY, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-VERIFY': xVerify,
        'Accept': 'application/json',
      },
      body: JSON.stringify({ request: payloadBase64 }),
      signal: controller.signal,
    });

    const data = await res.json().catch(() => ({}));

    transaction.responseData = data;
    transaction.errorMessage = '';

    if (data.success && data.code === 'PAYMENT_INITIATED') {
      const redirectInfo = data.data && data.data.instrumentResponse && data.data.instrumentResponse.redirectInfo;
      const paymentUrl = redirectInfo && redirectInfo.url;
      if (!paymentUrl) {
        transaction.errorMessage = 'PhonePe did not return a redirect URL';
        transaction.paymentStatus = 'failed';
        await transaction.save();
        throw new PhonePeError('PhonePe did not return a redirect URL.');
      }

      await transaction.save();

      order.transactionId = transaction.transactionId;
      order.paymentMethod = 'phonepe';
      order.paymentStatus = 'pending';
      await order.save();

      return { redirectUrl: paymentUrl, transactionId: transaction.transactionId, transaction };
    }

    transaction.paymentStatus = 'failed';
    transaction.errorMessage = data.message || 'Payment initiation failed';
    await transaction.save();

    throw new PhonePeError(transaction.errorMessage);
  } catch (err) {
    clearTimeout(timeout);
    if (err instanceof PhonePeError) throw err;
    const message = err.name === 'AbortError' ? 'PhonePe request timed out.' : `PhonePe request failed: ${err.message}`;
    transaction.paymentStatus = 'failed';
    transaction.errorMessage = message;
    await transaction.save();
    throw new PhonePeError(message);
  }
}

function buildStatusXVerify(config, merchantTransactionId) {
  const endpoint = STATUS_PREFIX + config.merchantId + '/' + merchantTransactionId;
  const xVerify = buildXVerify('', endpoint, config.saltKey, config.saltIndex);
  return { endpoint, xVerify };
}

async function checkStatus(transactionId) {
  const config = getConfig();
  const { endpoint, xVerify } = buildStatusXVerify(config, transactionId);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);

  try {
    const res = await fetch(config.baseUrl + endpoint, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-VERIFY': xVerify,
        'X-MERCHANT-ID': config.merchantId,
        'Accept': 'application/json',
      },
      signal: controller.signal,
    });
    const data = await res.json().catch(() => ({}));
    return data;
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new PhonePeError('PhonePe status check timed out.', 'PHONEPE_TIMEOUT');
    }
    throw new PhonePeError(`PhonePe status check failed: ${err.message}`);
  } finally {
    clearTimeout(timeout);
  }
}

function verifyCallbackSignature(response, xVerifyHeader) {
  const config = getConfig();

  if (!response || !xVerifyHeader) {
    throw new PhonePeSignatureError('Missing callback response or X-VERIFY header.');
  }

  let decoded;
  try {
    decoded = JSON.parse(Buffer.from(response, 'base64').toString('utf-8'));
  } catch (err) {
    throw new PhonePeSignatureError('Callback response is not valid base64 JSON.');
  }

  const merchantTransactionId =
    decoded.data && decoded.data.merchantTransactionId;

  if (!merchantTransactionId) {
    throw new PhonePeSignatureError('merchantTransactionId not found in callback.');
  }

  const endpoint = STATUS_PREFIX + config.merchantId + '/' + merchantTransactionId;
  const expectedHash = crypto
    .createHash('sha256')
    .update(response + endpoint + config.saltKey)
    .digest('hex');
  const expectedChecksum = expectedHash + '###' + config.saltIndex;

  if (!safeEqual(expectedChecksum, xVerifyHeader)) {
    throw new PhonePeSignatureError('Callback checksum verification failed.');
  }

  return decoded;
}

function verifyWebhookSecret(req) {
  const secret = process.env.PHONEPE_WEBHOOK_SECRET;
  if (!secret) return true;
  const provided =
    req.headers['x-zipstore-webhook-secret'] ||
    req.headers['x-webhook-secret'] ||
    '';
  return safeEqual(secret, provided);
}

async function getTransaction(transactionId) {
  return PaymentTransaction.findOne({ transactionId });
}

async function syncOrderFromTransaction(transaction, extraData) {
  const order = await Order.findById(transaction.order);
  if (!order) return null;

  const data = extraData || transaction.responseData || {};
  const success = data.success === true;
  const code = data.code;

  if (success && code === 'PAYMENT_SUCCESS') {
    if (order.paymentStatus !== 'paid') {
      order.paymentStatus = 'paid';
      order.orderStatus = order.orderStatus === 'cancelled' ? 'pending' : order.orderStatus;
      await order.save();
    }
    if (transaction.paymentStatus !== 'success') {
      transaction.paymentStatus = 'success';
      transaction.paidAt = transaction.paidAt || new Date();
      await transaction.save();
    }
    return { changed: true, state: 'paid' };
  }

  if (data.state === 'COMPLETED' && data.code === 'PAYMENT_SUCCESS') {
    if (order.paymentStatus !== 'paid') {
      order.paymentStatus = 'paid';
      await order.save();
    }
    if (transaction.paymentStatus !== 'success') {
      transaction.paymentStatus = 'success';
      transaction.paidAt = transaction.paidAt || new Date();
      await transaction.save();
    }
    return { changed: true, state: 'paid' };
  }

  if (code && code.startsWith('PAYMENT_ERROR')) {
    if (order.paymentStatus !== 'failed') {
      order.paymentStatus = 'failed';
      await order.save();
    }
    if (transaction.paymentStatus !== 'failed') {
      transaction.paymentStatus = 'failed';
      transaction.errorMessage = data.message || code;
      await transaction.save();
    }
    return { changed: true, state: 'failed' };
  }

  return { changed: false, state: order.paymentStatus };
}

async function processWebhookCallback({ response, xVerifyHeader, ip }) {
  const decoded = verifyCallbackSignature(response, xVerifyHeader);

  const merchantTransactionId = decoded.data && decoded.data.merchantTransactionId;
  if (!merchantTransactionId) {
    throw new PhonePeSignatureError('merchantTransactionId missing after verification.');
  }

  let transaction = await getTransaction(merchantTransactionId);

  if (!transaction) {
    const order = await Order.findOne({ transactionId: merchantTransactionId });
    if (!order) {
      throw new PhonePeError('Unknown transaction in callback.', 'PHONEPE_UNKNOWN_TRANSACTION');
    }
    transaction = await PaymentTransaction.create({
      order: order._id,
      transactionId: merchantTransactionId,
      paymentMethod: order.paymentMethod || 'phonepe',
      paymentStatus: 'pending',
      amount: order.totalAmount,
      responseData: decoded,
    });
  }

  const result = await syncOrderFromTransaction(transaction, decoded);

  transaction.responseData = decoded;
  transaction.lastStatusCheckedAt = new Date();
  await transaction.save();

  return { decoded, transaction, result };
}

async function retryPayment({ order, mobileNumber, redirectUrl }) {
  const config = getConfig();
  let transaction = await PaymentTransaction.findOne({
    order: order._id,
    paymentStatus: 'pending',
  });

  if (transaction) {
    transaction.retryCount = (transaction.retryCount || 0) + 1;
    await transaction.save();
  }

  return initiatePayment({ order, mobileNumber, redirectUrl });
}

async function refund({ transactionId, amount, refundId }) {
  const config = getConfig();
  const transaction = await PaymentTransaction.findOne({ transactionId });
  if (!transaction) {
    throw new PhonePeError('Transaction not found.', 'PHONEPE_TRANSACTION_NOT_FOUND');
  }

  const payload = {
    merchantId: config.merchantId,
    merchantTransactionId: transaction.transactionId,
    merchantRefundId: refundId || ('REF_' + Date.now() + '_' + crypto.randomBytes(3).toString('hex').toUpperCase()),
    amount: amountToPaise(amount || transaction.amount),
    callbackUrl: config.callbackUrl,
  };

  const payloadBase64 = Buffer.from(JSON.stringify(payload), 'utf-8').toString('base64');
  const xVerify = buildXVerify(payloadBase64, REFUND, config.saltKey, config.saltIndex);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);

  try {
    const res = await fetch(config.baseUrl + REFUND, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-VERIFY': xVerify,
        'Accept': 'application/json',
      },
      body: JSON.stringify({ request: payloadBase64 }),
      signal: controller.signal,
    });
    const data = await res.json().catch(() => ({}));

    if (data.success) {
      transaction.paymentStatus = 'refunded';
      transaction.refundedAt = new Date();
      transaction.responseData = data;
      await transaction.save();
    }
    return data;
  } catch (err) {
    clearTimeout(timeout);
    throw new PhonePeError(`Refund request failed: ${err.message}`);
  } finally {
    clearTimeout(timeout);
  }
}

module.exports = {
  PhonePeError,
  PhonePeConfigError,
  PhonePeSignatureError,
  getConfig,
  generateTransactionId,
  initiatePayment,
  checkStatus,
  verifyCallbackSignature,
  verifyWebhookSecret,
  processWebhookCallback,
  getTransaction,
  retryPayment,
  refund,
  syncOrderFromTransaction,
  buildStatusXVerify,
  amountToPaise,
};
