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

module.exports = mongoose.model('Product', productSchema);
