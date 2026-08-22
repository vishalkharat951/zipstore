const mongoose = require('mongoose');

const productSchema = new mongoose.Schema({
  title: {
    type: String,
    required: [true, 'Product title is required'],
    trim: true,
  },
  description: {
    type: String,
    required: [true, 'Product description is required'],
  },
  price: {
    type: Number,
    required: [true, 'Product price is required'],
    min: 0,
  },
  category: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Category',
    required: [true, 'Product category is required'],
  },
  images: {
    type: [String],
    default: [],
  },
  thumbnail: {
    type: String,
    default: '',
  },
  videoUrl: {
    type: String,
    default: '',
  },
  stock: {
    type: Number,
    required: [true, 'Stock count is required'],
    min: 0,
    default: 0,
  },
}, { timestamps: true });

productSchema.index({ category: 1, createdAt: -1 });
productSchema.index({ price: 1 });
productSchema.index({ createdAt: -1 });

module.exports = mongoose.model('Product', productSchema);
