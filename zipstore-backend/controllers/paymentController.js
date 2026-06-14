const crypto = require('crypto');
const Order = require('../models/Order');

const UPI_ID = '8669303401@ybl';
const MERCHANT_NAME = 'ZipStore';


function generateUPIUrl(amount, orderId, transactionRef) {
  const tn = `Order ${orderId}`;
  return (
    `upi://pay?pa=${UPI_ID}` +
    `&pn=${encodeURIComponent(MERCHANT_NAME)}` +
    `&am=${amount.toFixed(2)}` +
    `&tn=${encodeURIComponent(tn)}` +
    `&tr=${transactionRef}` +
    `&cu=INR`
  );
}


exports.initiateUPI = async (req, res, next) => {
  try {
    const { orderId } = req.body;

    if (!orderId) {
      return res.status(400).json({ error: 'orderId is required' });
    }

    const order = await Order.findById(orderId);
    if (!order) {
      return res.status(404).json({ error: 'Order not found' });
    }

    if (order.paymentStatus === 'paid') {
      return res.status(400).json({ error: 'Order is already paid' });
    }

    const transactionRef = 'UPI_' + Date.now() + '_' + Math.random().toString(36).substring(2, 8).toUpperCase();
    const upiUrl = generateUPIUrl(order.totalAmount, order._id, transactionRef);

    order.paymentMethod = 'upi';
    order.transactionId = transactionRef;
    order.paymentStatus = 'pending';
    await order.save();

    res.json({
      success: true,
      upiUrl,
      transactionRef,
      upiId: UPI_ID,
      merchantName: MERCHANT_NAME,
      amount: order.totalAmount,
      order: {
        id: order._id,
        paymentStatus: order.paymentStatus,
        orderStatus: order.orderStatus,
      },
    });
  } catch (err) {
    next(err);
  }
};

exports.checkoutMock = async (req, res, next) => {
  try {
    const { orderId } = req.body;

    if (!orderId) {
      return res.status(400).json({ error: 'orderId is required' });
    }

    const order = await Order.findById(orderId);
    if (!order) {
      return res.status(404).json({ error: 'Order not found' });
    }

    if (order.paymentStatus === 'paid') {
      return res.status(400).json({ error: 'Order is already paid' });
    }

    const mockToken = 'mocked_payment_token_' + Date.now();

    order.paymentStatus = 'paid';
    order.paymentMethod = 'mock';
    order.transactionId = mockToken;
    await order.save();

    res.json({
      message: 'Payment successful (mock)',
      mockToken,
      order: {
        id: order._id,
        paymentStatus: order.paymentStatus,
        orderStatus: order.orderStatus,
        totalAmount: order.totalAmount,
      },
    });
  } catch (err) {
    next(err);
  }
};

exports.initiatePhonePe = async (req, res, next) => {
  try {
    const { orderId } = req.body;

    if (!orderId) {
      return res.status(400).json({ error: 'orderId is required' });
    }

    const order = await Order.findById(orderId);
    if (!order) {
      return res.status(404).json({ error: 'Order not found' });
    }

    if (order.paymentStatus === 'paid') {
      return res.status(400).json({ error: 'Order is already paid' });
    }

    const merchantId = process.env.PHONEPE_MERCHANT_ID || 'MERCHANTUAT';
    const saltKey = process.env.PHONEPE_SALT_KEY || '96434309-7796-489d-8924-ab56988a6076';
    const saltIndex = process.env.PHONEPE_SALT_INDEX || '1';
    const isProd = process.env.PHONEPE_ENV === 'production';
    const baseUrl = isProd
      ? 'https://api.phonepe.com/apis/hermes'
      : 'https://api-preprod.phonepe.com/apis/hermes';

    const transactionId = 'TXN_' + Date.now() + '_' + Math.random().toString(36).substring(2, 8);

    const amountPaise = Math.round(order.totalAmount * 100);

    const callbackUrl = process.env.PHONEPE_CALLBACK_URL || `https://zip-backend-myp0.onrender.com/api/payments/phonepe-callback`;

    const payload = {
      merchantId,
      merchantTransactionId: transactionId,
      merchantUserId: 'MUID_' + (req.user ? req.user.id : 'guest'),
      amount: amountPaise,
      redirectUrl: `${process.env.FRONTEND_URL || 'https://vishalkharat951.github.io'}/my-orders.html`,
      redirectMode: 'POST',
      callbackUrl,
      mobileNumber: '',
      paymentInstrument: { type: 'PAY_PAGE' },
    };

    const payloadJson = JSON.stringify(payload);
    const payloadBase64 = Buffer.from(payloadJson).toString('base64');

    const stringToSign = payloadBase64 + '/pg/v1/pay' + saltKey;
    const sha256 = crypto.createHash('sha256').update(stringToSign).digest('hex');
    const xVerify = sha256 + '###' + saltIndex;

    const phonepeRes = await fetch(`${baseUrl}/pg/v1/pay`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-VERIFY': xVerify,
      },
      body: JSON.stringify({ request: payloadBase64 }),
    });

    const phonepeData = await phonepeRes.json();

    if (phonepeData.success) {
      order.transactionId = transactionId;
      order.paymentMethod = 'phonepe';
      await order.save();

      return res.json({
        success: true,
        redirectUrl: phonepeData.data.instrumentResponse.redirectInfo.url,
        transactionId,
      });
    }

    res.status(502).json({ error: 'PhonePe initiation failed', details: phonepeData });
  } catch (err) {
    next(err);
  }
};

exports.phonePeCallback = async (req, res, next) => {
  try {
    const { response } = req.body;

    if (!response) {
      return res.status(400).json({ error: 'Missing response' });
    }

    const decoded = JSON.parse(Buffer.from(response, 'base64').toString('utf-8'));

    const order = await Order.findOne({ transactionId: decoded.merchantTransactionId });
    if (!order) {
      return res.status(404).json({ error: 'Order not found for transaction' });
    }

    if (decoded.code === 'PAYMENT_SUCCESS') {
      order.paymentStatus = 'paid';
      await order.save();
      res.redirect(`${process.env.FRONTEND_URL || 'https://vishalkharat951.github.io'}/my-orders.html?payment=success`);
    } else {
      order.paymentStatus = 'failed';
      await order.save();
      res.redirect(`${process.env.FRONTEND_URL || 'https://vishalkharat951.github.io'}/checkout.html?payment=failed`);
    }
  } catch (err) {
    next(err);
  }
};

exports.verifyPhonePeStatus = async (req, res, next) => {
  try {
    const { transactionId } = req.params;

    if (!transactionId) {
      return res.status(400).json({ error: 'transactionId is required' });
    }

    const merchantId = process.env.PHONEPE_MERCHANT_ID || 'MERCHANTUAT';
    const saltKey = process.env.PHONEPE_SALT_KEY || '96434309-7796-489d-8924-ab56988a6076';
    const saltIndex = process.env.PHONEPE_SALT_INDEX || '1';
    const isProd = process.env.PHONEPE_ENV === 'production';
    const baseUrl = isProd
      ? 'https://api.phonepe.com/apis/hermes'
      : 'https://api-preprod.phonepe.com/apis/hermes';

    const stringToSign = `/pg/v1/status/${merchantId}/${transactionId}` + saltKey;
    const sha256 = crypto.createHash('sha256').update(stringToSign).digest('hex');
    const xVerify = sha256 + '###' + saltIndex;

    const phonepeRes = await fetch(
      `${baseUrl}/pg/v1/status/${merchantId}/${transactionId}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'X-VERIFY': xVerify,
          'X-MERCHANT-ID': merchantId,
        },
      }
    );

    const phonepeData = await phonepeRes.json();

    if (phonepeData.success && phonepeData.code === 'PAYMENT_SUCCESS') {
      const order = await Order.findOne({ transactionId });
      if (order && order.paymentStatus !== 'paid') {
        order.paymentStatus = 'paid';
        await order.save();
      }
    }

    res.json(phonepeData);
  } catch (err) {
    next(err);
  }
};
