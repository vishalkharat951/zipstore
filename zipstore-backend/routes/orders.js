const express = require('express');
const router = express.Router();
const orderController = require('../controllers/orderController');
const { authenticate, optionalAuth, isAdmin } = require('../middleware/auth');
const { validateBody } = require('../middleware/security');

const orderItemSchema = {
  productId: { type: 'string', required: true, max: 120 },
  quantity: { type: 'number', required: true, min: 1, max: 999 },
};

router.post(
  '/orders',
  optionalAuth,
  validateBody({
    items: { type: 'array', required: true },
    shippingAddress: { type: 'object', required: true },
  }),
  orderController.createOrder
);
router.get('/orders/my', authenticate, orderController.getMyOrders);
router.get('/orders/guest', orderController.getGuestOrders);
router.get('/orders/:id', authenticate, orderController.getOrderById);
router.get('/admin/orders', authenticate, isAdmin, orderController.getAdminOrders);
router.patch('/admin/orders/:id', authenticate, isAdmin, orderController.updateOrderStatus);
router.delete('/admin/orders/:id', authenticate, isAdmin, orderController.deleteOrder);

module.exports = router;
