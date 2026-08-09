const mongoose = require('mongoose');

const orderItemSchema = new mongoose.Schema({
  productId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Product',
    required: true,
  },
  quantity: {
    type: Number,
    required: true,
    min: 1,
  },
  price: {
    type: Number,
    required: true,
    min: 0,
  },
}, { _id: false });

const orderSchema = new mongoose.Schema({
  userId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    default: null,
    index: true,
  },
  clientOrderId: {
    type: String,
    default: '',
    index: true,
  },
  orderCode: {
    type: String,
    default: '',
    unique: true,
    sparse: true,
    index: true,
  },
  items: {
    type: [orderItemSchema],
    validate: {
      validator: function (arr) { return arr.length > 0; },
      message: 'Order must contain at least one item',
    },
  },
  totalAmount: {
    type: Number,
    required: true,
    min: 0,
  },
  shippingAddress: {
    name: { type: String, default: '' },
    phone: { type: String, default: '' },
    street: { type: String, required: true },
    city: { type: String, required: true },
    state: { type: String, required: true },
    zip: { type: String, default: '' },
    country: { type: String, default: '' },
  },
  paymentMethod: {
    type: String,
    enum: ['phonepe', 'upi'],
    default: 'upi',
  },
  transactionId: {
    type: String,
    default: '',
  },
  paymentStatus: {
    type: String,
    enum: ['pending', 'paid', 'failed', 'refunded'],
    default: 'pending',
  },
  orderStatus: {
    type: String,
    enum: ['pending', 'confirmed', 'processing', 'packed', 'shipped', 'out_for_delivery', 'delivered', 'cancelled'],
    default: 'pending',
  },
  estimatedDeliveryDate: {
    type: Date,
    default: null,
  },
}, { timestamps: true });

orderSchema.index({ userId: 1, createdAt: -1 });

module.exports = mongoose.model('Order', orderSchema);
