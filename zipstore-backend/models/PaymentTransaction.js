const mongoose = require('mongoose');

const paymentTransactionSchema = new mongoose.Schema({
  order: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Order',
    required: true,
  },
  transactionId: {
    type: String,
    required: true,
    unique: true,
    index: true,
  },
  paymentMethod: {
    type: String,
    enum: ['phonepe', 'upi'],
    default: 'phonepe',
  },
  paymentStatus: {
    type: String,
    enum: ['pending', 'success', 'failed', 'refunded'],
    default: 'pending',
    index: true,
  },
  amount: {
    type: Number,
    required: true,
    min: 0,
  },
  currency: {
    type: String,
    default: 'INR',
  },
  requestPayload: {
    type: Object,
    default: {},
  },
  responseData: {
    type: Object,
    default: {},
  },
  errorMessage: {
    type: String,
    default: '',
  },
  retryCount: {
    type: Number,
    default: 0,
  },
  lastStatusCheckedAt: {
    type: Date,
    default: null,
  },
  paidAt: {
    type: Date,
    default: null,
  },
  refundedAt: {
    type: Date,
    default: null,
  },
}, { timestamps: true });

paymentTransactionSchema.index({ order: 1, paymentStatus: 1 });

module.exports = mongoose.model('PaymentTransaction', paymentTransactionSchema);
