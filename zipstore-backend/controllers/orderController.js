const crypto = require('crypto');
const Order = require('../models/Order');
const Product = require('../models/Product');

const VALID_ORDER_STATUSES = ['pending', 'confirmed', 'processing', 'packed', 'shipped', 'out_for_delivery', 'delivered', 'cancelled'];
const VALID_PAYMENT_STATUSES = ['pending', 'paid', 'failed', 'refunded'];

const INDIAN_PHONE_RE = /^(\+91[\s-]?)?[6-9]\d{9}$/;

function generateOrderCode() {
  return 'ZS' + crypto.randomBytes(8).toString('hex').toUpperCase();
}

function parseQuantity(value) {
  const qty = Number(value);
  if (!Number.isInteger(qty) || qty < 1 || qty > 999) return null;
  return qty;
}

function validateShippingAddress(address) {
  const errors = [];
  if (!address || typeof address !== 'object') return ['A shipping address is required'];
  if (!address.name || String(address.name).trim().length < 2) errors.push('Full name is required');
  if (!address.phone || !INDIAN_PHONE_RE.test(String(address.phone).trim())) errors.push('A valid 10-digit Indian mobile number is required');
  if (!address.street || String(address.street).trim().length < 5) errors.push('A complete delivery address is required');
  if (!address.city || !String(address.city).trim()) errors.push('City is required');
  if (!address.state || !String(address.state).trim()) errors.push('State is required');
  if (address.zip && !/^\d{6}$/.test(String(address.zip).trim())) errors.push('PIN code must be 6 digits');
  return errors;
}

exports.createOrder = async (req, res, next) => {
  try {
    const { items, shippingAddress, clientOrderId } = req.body;

    if (!items || !items.length) {
      return res.status(400).json({ error: 'Order must contain at least one item' });
    }

    const addressErrors = validateShippingAddress(shippingAddress);
    if (addressErrors.length) {
      return res.status(400).json({ error: addressErrors.join('. ') });
    }

    if (clientOrderId) {
      const existing = await Order.findOne({ clientOrderId });
      if (existing) {
        return res.status(409).json({ error: 'Duplicate order detected', order: existing });
      }
    }

    const mergedItems = new Map();
    for (const item of items) {
      if (typeof item.productId !== 'string' || !item.productId) {
        return res.status(400).json({ error: 'Invalid product ID in order item' });
      }
      const qty = parseQuantity(item.quantity);
      if (qty === null) {
        return res.status(400).json({ error: 'Invalid quantity for an order item' });
      }
      mergedItems.set(item.productId, (mergedItems.get(item.productId) || 0) + qty);
    }

    const productIds = Array.from(mergedItems.keys());
    const products = await Product.find({ _id: { $in: productIds } });

    if (products.length !== productIds.length) {
      return res.status(400).json({ error: 'One or more products not found' });
    }

    const productMap = {};
    for (const p of products) {
      productMap[p._id.toString()] = p;
    }

    const orderItems = [];
    for (const [productId, quantity] of mergedItems) {
      const product = productMap[productId];
      if (!product) {
        return res.status(400).json({ error: 'One or more products not found' });
      }
      if (product.stock < quantity) {
        return res.status(400).json({ error: `Insufficient stock for ${product.title}` });
      }
      const price = Number(product.price);
      orderItems.push({ productId, quantity, price });
    }

    const totalAmount = orderItems.reduce((sum, item) => sum + item.price * item.quantity, 0);

    const order = await Order.create({
      userId: req.user ? req.user.id : null,
      orderCode: generateOrderCode(),
      items: orderItems,
      totalAmount: Math.round(totalAmount * 100) / 100,
      shippingAddress,
      clientOrderId: clientOrderId || undefined,
      estimatedDeliveryDate: new Date(Date.now() + 4 * 24 * 60 * 60 * 1000),
    });

    for (const item of orderItems) {
      const result = await Product.updateOne(
        { _id: item.productId, stock: { $gte: item.quantity } },
        { $inc: { stock: -item.quantity } }
      );
      if (result.modifiedCount === 0) {
        await Order.findByIdAndDelete(order._id);
        const product = productMap[item.productId];
        return res.status(400).json({ error: `Insufficient stock for ${product ? product.title : 'a product'}` });
      }
    }

    res.status(201).json({ message: 'Order created', order });
  } catch (err) {
    next(err);
  }
};

function parseOrderPagination(query) {
  const page = Math.max(1, parseInt(query.page, 10) || 1);
  const limit = Math.min(200, Math.max(1, parseInt(query.limit, 10) || 100));
  return { page, limit, skip: (page - 1) * limit };
}

exports.getAdminOrders = async (req, res, next) => {
  try {
    const { page, limit, skip } = parseOrderPagination(req.query);
    const filter = {};
    if (req.query.status && VALID_ORDER_STATUSES.includes(req.query.status)) {
      filter.orderStatus = req.query.status;
    }
    const [orders, total] = await Promise.all([
      Order.find(filter)
        .populate('userId', 'name email')
        .populate('items.productId', 'title price')
        .sort('-createdAt')
        .skip(skip)
        .limit(limit)
        .lean(),
      Order.countDocuments(filter),
    ]);
    res.json({ count: orders.length, total, page, pages: Math.ceil(total / limit), orders });
  } catch (err) {
    next(err);
  }
};

exports.getMyOrders = async (req, res, next) => {
  try {
    const { page, limit, skip } = parseOrderPagination(req.query);
    const filter = { userId: req.user.id };
    const [orders, total] = await Promise.all([
      Order.find(filter)
        .populate('items.productId', 'title price images')
        .sort('-createdAt')
        .skip(skip)
        .limit(limit)
        .lean(),
      Order.countDocuments(filter),
    ]);
    res.json({ count: orders.length, total, page, pages: Math.ceil(total / limit), orders });
  } catch (err) {
    next(err);
  }
};

exports.getOrderById = async (req, res, next) => {
  try {
    const order = await Order.findById(req.params.id)
      .populate('items.productId', 'title price images')
      .populate('userId', 'name email');
    if (!order) {
      return res.status(404).json({ error: 'Order not found' });
    }
    if (order.userId) {
      if (String(order.userId._id || order.userId) !== String(req.user.id)) {
        return res.status(403).json({ error: 'Access denied' });
      }
    } else if (req.user.role !== 'admin') {
      return res.status(403).json({ error: 'Access denied. Guest orders are tracked by order code.' });
    }
    res.json({ order });
  } catch (err) {
    next(err);
  }
};

exports.updateOrderStatus = async (req, res, next) => {
  try {
    const { orderStatus, paymentStatus } = req.body;

    const update = {};
    if (orderStatus !== undefined && orderStatus !== null && orderStatus !== '') {
      if (!VALID_ORDER_STATUSES.includes(orderStatus)) {
        return res.status(400).json({ error: 'Invalid order status' });
      }
      update.orderStatus = orderStatus;
    }
    if (paymentStatus !== undefined && paymentStatus !== null && paymentStatus !== '') {
      if (!VALID_PAYMENT_STATUSES.includes(paymentStatus)) {
        return res.status(400).json({ error: 'Invalid payment status' });
      }
      update.paymentStatus = paymentStatus;
    }

    if (!Object.keys(update).length) {
      return res.status(400).json({ error: 'Provide orderStatus or paymentStatus to update' });
    }

    const current = await Order.findById(req.params.id);
    if (!current) {
      return res.status(404).json({ error: 'Order not found' });
    }

    if (update.orderStatus && (current.orderStatus === 'delivered' || current.orderStatus === 'cancelled')) {
      return res.status(400).json({
        error: `Cannot change order status because the order is already ${current.orderStatus}.`,
      });
    }

    const order = await Order.findByIdAndUpdate(req.params.id, update, { new: true, runValidators: true });

    res.json({ message: 'Order updated', order });
  } catch (err) {
    next(err);
  }
};

exports.getGuestOrders = async (req, res, next) => {
  try {
    const { ids, codes } = req.query;
    const idArray = (ids || '').split(',').map(id => id.trim()).filter(Boolean);
    const codeArray = (codes || '').split(',').map(code => code.trim().toUpperCase()).filter(Boolean);

    if (!idArray.length && !codeArray.length) {
      return res.status(400).json({ error: 'Order IDs or codes are required' });
    }

    const match = { $or: [] };
    if (idArray.length) match.$or.push({ _id: { $in: idArray }, userId: null });
    if (codeArray.length) match.$or.push({ orderCode: { $in: codeArray } });

    const orders = await Order.find(match)
      .populate('items.productId', 'title price images')
      .sort('-createdAt')
      .lean();
    res.json({ count: orders.length, orders });
  } catch (err) {
    next(err);
  }
};

exports.deleteOrder = async (req, res, next) => {
  try {
    const order = await Order.findByIdAndDelete(req.params.id);
    if (!order) {
      return res.status(404).json({ error: 'Order not found' });
    }
    res.json({ message: 'Order deleted' });
  } catch (err) {
    next(err);
  }
};
