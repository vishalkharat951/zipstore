const express = require('express');
const router = express.Router();
const paymentController = require('../controllers/paymentController');
const { authenticate, optionalAuth, isAdmin } = require('../middleware/auth');
const { createRateLimiter, validateBody } = require('../middleware/security');

const paymentLimiter = createRateLimiter({
  windowMs: 60 * 1000,
  max: 30,
  message: 'Too many payment requests. Please slow down and try again.',
});

const webhookLimiter = createRateLimiter({
  windowMs: 60 * 1000,
  max: 120,
  message: 'Too many webhook requests.',
});

router.post(
  '/payments/upi-initiate',
  paymentLimiter,
  optionalAuth,
  validateBody({ orderId: { type: 'string', required: true, max: 120 } }),
  paymentController.initiateUPI
);

router.post(
  '/payments/phonepe-initiate',
  paymentLimiter,
  optionalAuth,
  validateBody({
    orderId: { type: 'string', required: true, max: 120 },
    mobileNumber: { type: 'string', max: 20 },
    redirectUrl: { type: 'string', max: 500 },
  }),
  paymentController.initiatePhonePe
);

router.post(
  '/payments/phonepe-retry',
  paymentLimiter,
  optionalAuth,
  validateBody({
    orderId: { type: 'string', required: true, max: 120 },
    mobileNumber: { type: 'string', max: 20 },
  }),
  paymentController.retryPhonePePayment
);

router.post(
  '/payments/phonepe-callback',
  webhookLimiter,
  express.urlencoded({ extended: true, limit: '2mb' }),
  paymentController.phonePeWebhook
);

router.get(
  '/payments/phonepe-status/:transactionId',
  paymentLimiter,
  authenticate,
  paymentController.verifyPhonePeStatus
);

router.get(
  '/payments/transaction/:transactionId',
  paymentLimiter,
  authenticate,
  paymentController.getTransactionStatus
);

router.post(
  '/admin/payments/refund/:transactionId',
  paymentLimiter,
  authenticate,
  isAdmin,
  paymentController.refundPayment
);

module.exports = router;
