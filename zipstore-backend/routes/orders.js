const express = require('express');
const router = express.Router();
const orderController = require('../controllers/orderController');
const paymentController = require('../controllers/paymentController');
const { authenticate } = require('../middleware/auth');

router.post('/orders', orderController.createOrder);
router.get('/orders/my', authenticate, orderController.getMyOrders);
router.post('/payments/checkout-mock', paymentController.checkoutMock);
router.post('/payments/phonepe-initiate', paymentController.initiatePhonePe);
router.post('/payments/phonepe-callback', paymentController.phonePeCallback);
router.get('/payments/phonepe-status/:transactionId', authenticate, paymentController.verifyPhonePeStatus);
router.post('/payments/upi-initiate', paymentController.initiateUPI);
router.get('/admin/orders', authenticate, orderController.getAdminOrders);
router.patch('/admin/orders/:id', authenticate, orderController.updateOrderStatus);
router.delete('/admin/orders/:id', authenticate, orderController.deleteOrder);

module.exports = router;
