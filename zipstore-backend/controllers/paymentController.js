const crypto = require('crypto');
const Order = require('../models/Order');
const PaymentTransaction = require('../models/PaymentTransaction');
const phonepe = require('../services/phonepe');

const UPI_ID = (process.env.UPI_ID || '').trim();
const MERCHANT_NAME = process.env.MERCHANT_NAME || 'ZipStore';
const CURRENCY = 'INR';

function generateUPIUrl(amount, orderId, transactionRef) {
  const tn = `Order ${orderId}`;
  return (
    `upi://pay?pa=${encodeURIComponent(UPI_ID)}` +
    `&pn=${encodeURIComponent(MERCHANT_NAME)}` +
    `&am=${amount.toFixed(2)}` +
    `&tn=${encodeURIComponent(tn)}` +
    `&tr=${encodeURIComponent(transactionRef)}` +
    `&cu=${CURRENCY}`
  );
}

async function findOwnedOrder(orderId, req) {
  let query = { _id: orderId };
  if (req.user) query.userId = req.user.id;
  return Order.findById(query);
}

exports.initiateUPI = async (req, res, next) => {
  try {
    if (!UPI_ID) {
      return res.status(503).json({
        error: 'UPI is not configured yet. Please pay after confirmation or contact support.',
      });
    }

    const { orderId } = req.body;

    const order = await findOwnedOrder(orderId, req);
    if (!order) {
      return res.status(404).json({ error: 'Order not found' });
    }
    if (order.paymentStatus === 'paid') {
      return res.status(400).json({ error: 'Order is already paid' });
    }

    const transactionRef = 'UPI_' + Date.now() + '_' + crypto.randomBytes(3).toString('hex').toUpperCase();

    let transaction = await PaymentTransaction.findOne({ order: order._id, paymentStatus: 'pending' });
    if (!transaction) {
      transaction = await PaymentTransaction.create({
        order: order._id,
        transactionId: transactionRef,
        paymentMethod: 'upi',
        paymentStatus: 'pending',
        amount: order.totalAmount,
      });
    }

    const upiUrl = generateUPIUrl(order.totalAmount, order._id, transaction.transactionId);

    order.paymentMethod = 'upi';
    order.transactionId = transaction.transactionId;
    order.paymentStatus = 'pending';
    await order.save();

    res.json({
      success: true,
      upiUrl,
      transactionRef: transaction.transactionId,
      upiId: UPI_ID,
      merchantName: MERCHANT_NAME,
      amount: order.totalAmount,
      order: {
        id: order._id,
        orderCode: order.orderCode,
        paymentStatus: order.paymentStatus,
        orderStatus: order.orderStatus,
      },
    });
  } catch (err) {
    next(err);
  }
};

exports.initiatePhonePe = async (req, res, next) => {
  try {
    const { orderId, mobileNumber } = req.body;

    const order = await findOwnedOrder(orderId, req);
    if (!order) {
      return res.status(404).json({ error: 'Order not found' });
    }
    if (order.paymentStatus === 'paid') {
      return res.status(400).json({ error: 'Order is already paid' });
    }

    const result = await phonepe.initiatePayment({
      order,
      mobileNumber,
      redirectUrl: req.body.redirectUrl,
    });

    return res.json({
      success: true,
      redirectUrl: result.redirectUrl,
      transactionId: result.transactionId,
    });
  } catch (err) {
    if (err.code === 'PHONEPE_CONFIG_ERROR') {
      return res.status(503).json({ error: err.message });
    }
    next(err);
  }
};

exports.phonePeWebhook = async (req, res, next) => {
  try {
    if (!phonepe.verifyWebhookSecret(req)) {
      return res.status(401).json({ error: 'Invalid webhook secret' });
    }

    const { response } = req.body;

    const result = await phonepe.processWebhookCallback({
      response,
      xVerifyHeader: req.headers['x-verify'],
      ip: req.ip,
    });

    res.status(200).json({
      status: 'OK',
      transactionId: result.decoded.data && result.decoded.data.merchantTransactionId,
      orderState: result.result.state,
    });
  } catch (err) {
    if (err.code === 'PHONEPE_SIGNATURE_ERROR') {
      return res.status(400).json({ error: 'Verification failed' });
    }
    if (err.code === 'PHONEPE_UNKNOWN_TRANSACTION') {
      return res.status(400).json({ error: 'Unknown transaction' });
    }
    next(err);
  }
};

exports.verifyPhonePeStatus = async (req, res, next) => {
  try {
    const { transactionId } = req.params;

    if (!transactionId) {
      return res.status(400).json({ error: 'transactionId is required' });
    }

    let transaction = await PaymentTransaction.findOne({ transactionId });

    if (!transaction) {
      const order = await Order.findOne({ transactionId });
      if (order) {
        transaction = await PaymentTransaction.create({
          order: order._id,
          transactionId,
          paymentMethod: order.paymentMethod || 'phonepe',
          paymentStatus: 'pending',
          amount: order.totalAmount,
        });
      }
    }

    let data;
    try {
      data = await phonepe.checkStatus(transactionId);
    } catch (err) {
      if (err.code === 'PHONEPE_TIMEOUT') {
        return res.status(504).json({ error: err.message });
      }
      return res.status(502).json({ error: err.message });
    }

    if (transaction) {
      transaction.responseData = data;
      transaction.lastStatusCheckedAt = new Date();
      await transaction.save();

      const sync = await phonepe.syncOrderFromTransaction(transaction, data);
      data.sync = sync;
    }

    res.json(data);
  } catch (err) {
    next(err);
  }
};

exports.retryPhonePePayment = async (req, res, next) => {
  try {
    const { orderId, mobileNumber } = req.body;

    const order = await findOwnedOrder(orderId, req);
    if (!order) {
      return res.status(404).json({ error: 'Order not found' });
    }
    if (order.paymentStatus === 'paid') {
      return res.status(400).json({ error: 'Order is already paid' });
    }

    const result = await phonepe.retryPayment({
      order,
      mobileNumber,
      redirectUrl: req.body.redirectUrl,
    });

    res.json({
      success: true,
      redirectUrl: result.redirectUrl,
      transactionId: result.transactionId,
    });
  } catch (err) {
    if (err.code === 'PHONEPE_CONFIG_ERROR') {
      return res.status(503).json({ error: err.message });
    }
    next(err);
  }
};

exports.getTransactionStatus = async (req, res, next) => {
  try {
    const { transactionId } = req.params;
    const transaction = await PaymentTransaction.findOne({ transactionId }).populate('order');

    if (!transaction) {
      return res.status(404).json({ error: 'Transaction not found' });
    }

    const order = transaction.order;
    if (order && order.userId) {
      if (String(order.userId._id || order.userId) !== String(req.user.id) && req.user.role !== 'admin') {
        return res.status(403).json({ error: 'Access denied' });
      }
    }

    res.json({
      transactionId: transaction.transactionId,
      paymentStatus: transaction.paymentStatus,
      paymentMethod: transaction.paymentMethod,
      amount: transaction.amount,
      currency: transaction.currency,
      retryCount: transaction.retryCount,
      paidAt: transaction.paidAt,
      createdAt: transaction.createdAt,
      updatedAt: transaction.updatedAt,
    });
  } catch (err) {
    next(err);
  }
};

exports.refundPayment = async (req, res, next) => {
  try {
    const { transactionId } = req.params;
    const { amount } = req.body;

    const result = await phonepe.refund({ transactionId, amount });

    const order = await Order.findOne({ transactionId });
    if (order && result.success) {
      order.paymentStatus = 'refunded';
      await order.save();
    }

    res.json(result);
  } catch (err) {
    next(err);
  }
};
