const Category = require('../models/Category');

exports.getCategories = async (req, res, next) => {
  try {
    const categories = await Category.find().populate('parent', 'name slug').sort('name');
    res.json({ count: categories.length, categories });
  } catch (err) {
    next(err);
  }
};

exports.getCategory = async (req, res, next) => {
  try {
    const category = await Category.findById(req.params.id).populate('parent', 'name slug');
    if (!category) {
      return res.status(404).json({ error: 'Category not found' });
    }
    res.json(category);
  } catch (err) {
    next(err);
  }
};

exports.createCategory = async (req, res, next) => {
  try {
    const { name, slug, parent, image } = req.body;

    if (!name || !slug) {
      return res.status(400).json({ error: 'name and slug are required' });
    }

    const existing = await Category.findOne({
      $or: [
        { name, parent: parent || null },
        { slug, parent: parent || null },
      ],
    });
    if (existing) {
      return res.status(409).json({ error: 'A category with this name or slug already exists under this parent' });
    }

    const category = await Category.create({
      name,
      slug,
      parent: parent || null,
      image: image || '',
    });
    res.status(201).json({ message: 'Category created', category });
  } catch (err) {
    next(err);
  }
};

exports.updateCategory = async (req, res, next) => {
  try {
    const { name, slug, parent, image } = req.body;

    const duplicate = await Category.findOne({
      _id: { $ne: req.params.id },
      $or: [
        { name, parent: parent || null },
        { slug, parent: parent || null },
      ],
    });
    if (duplicate) {
      return res.status(409).json({ error: 'Another category with this name or slug already exists under this parent' });
    }

    const category = await Category.findByIdAndUpdate(
      req.params.id,
      { name, slug, parent: parent || null, image },
      { new: true, runValidators: true }
    );

    if (!category) {
      return res.status(404).json({ error: 'Category not found' });
    }

    res.json({ message: 'Category updated', category });
  } catch (err) {
    next(err);
  }
};

exports.deleteCategory = async (req, res, next) => {
  try {
    const childrenCount = await Category.countDocuments({ parent: req.params.id });
    if (childrenCount > 0) {
      return res.status(400).json({ error: `Cannot delete: ${childrenCount} subcategory(ies) exist under this category` });
    }

    const productCount = await require('../models/Product').countDocuments({ category: req.params.id });
    if (productCount > 0) {
      return res.status(400).json({ error: `Cannot delete: ${productCount} product(s) are linked to this category` });
    }

    const category = await Category.findByIdAndDelete(req.params.id);
    if (!category) {
      return res.status(404).json({ error: 'Category not found' });
    }

    res.json({ message: 'Category deleted' });
  } catch (err) {
    next(err);
  }
};
