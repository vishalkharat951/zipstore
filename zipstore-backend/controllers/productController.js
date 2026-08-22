const Product = require('../models/Product');

exports.getProducts = async (req, res, next) => {
  try {
    const filter = {};
    if (req.query.category) {
      filter.category = req.query.category;
    }

    const products = await Product.find(filter).populate('category', 'name slug parent');
    res.json({ count: products.length, products });
  } catch (err) {
    next(err);
  }
};

exports.getProduct = async (req, res, next) => {
  try {
    const product = await Product.findById(req.params.id).populate('category', 'name slug parent');
    if (!product) {
      return res.status(404).json({ error: 'Product not found' });
    }
    res.json(product);
  } catch (err) {
    next(err);
  }
};

exports.createProduct = async (req, res, next) => {
  try {
    const { title, description, price, category, images, videoUrl, stock } = req.body;

    if (!title || !description || !price || !category || stock === undefined) {
      return res.status(400).json({ error: 'title, description, price, category, and stock are required' });
    }

    const product = await Product.create({
      title,
      description,
      price,
      category,
      images: Array.isArray(images) ? images : [],
      videoUrl,
      stock,
    });
    res.status(201).json({ message: 'Product created', product });
  } catch (err) {
    next(err);
  }
};

exports.updateProduct = async (req, res, next) => {
  try {
    const updateData = { ...req.body };
    if (updateData.images && !Array.isArray(updateData.images)) {
      updateData.images = [];
    }

    const product = await Product.findByIdAndUpdate(req.params.id, updateData, {
      new: true,
      runValidators: true,
    });

    if (!product) {
      return res.status(404).json({ error: 'Product not found' });
    }

    res.json({ message: 'Product updated', product });
  } catch (err) {
    next(err);
  }
};

exports.deleteProduct = async (req, res, next) => {
  try {
    const product = await Product.findByIdAndDelete(req.params.id);
    if (!product) {
      return res.status(404).json({ error: 'Product not found' });
    }
    res.json({ message: 'Product deleted' });
  } catch (err) {
    next(err);
  }
};
