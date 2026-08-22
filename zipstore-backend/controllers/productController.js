const Product = require('../models/Product');

// Optional image processing library. When available, listing endpoints return
// small generated thumbnails instead of full-size base64 images (big win on
// payload size). If it is not installed, we fall back to the first full image.
let sharp = null;
try {
  sharp = require('sharp');
} catch (_) {
  // sharp unavailable (e.g. not installed on the host) — degrade gracefully
}

const THUMB_MAX = 360;

function escapeRegExp(str) {
  return String(str).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function firstImage(product) {
  if (product.images && product.images.length) return product.images[0];
  if (product.imageUrl) {
    if (product.imageUrl[0] === '[') {
      try {
        const parsed = JSON.parse(product.imageUrl);
        if (Array.isArray(parsed) && parsed.length) return parsed[0];
      } catch (_) {}
      return '';
    }
    return product.imageUrl;
  }
  return '';
}

async function buildThumbnail(imageDataUri) {
  if (!sharp || !imageDataUri) return '';
  const match = /^data:image\/([a-z0-9+]+);base64,/.exec(imageDataUri);
  if (!match) return '';
  const mime = match[1].toLowerCase();
  const base64 = imageDataUri.slice(match[0].length);
  const buffer = Buffer.from(base64, 'base64');
  if (!buffer.length) return '';
  try {
    const out = await sharp(buffer)
      .rotate()
      .resize(THUMB_MAX, THUMB_MAX, { fit: 'inside', withoutEnlargement: true })
      .webp({ quality: 68 })
      .toBuffer();
    const mimeOut = mime === 'png' ? 'image/png' : 'image/webp';
    return `data:${mimeOut};base64,${out.toString('base64')}`;
  } catch (_) {
    return '';
  }
}

async function ensureThumbnails(products) {
  const missing = products.filter(p => !p.thumbnail);
  if (!missing.length) return;
  const updates = await Promise.all(missing.map(async (p) => {
    const thumb = await buildThumbnail(firstImage(p));
    return thumb ? { _id: p._id, thumb } : null;
  }));
  for (const u of updates) {
    if (!u) continue;
    const target = missing.find(p => String(p._id) === String(u._id));
    if (target) target.thumbnail = u.thumb;
    try {
      await Product.updateOne({ _id: u._id }, { $set: { thumbnail: u.thumb } });
    } catch (_) {}
  }
}

function parsePagination(query) {
  const page = Math.max(1, parseInt(query.page, 10) || 1);
  const limit = Math.min(200, Math.max(1, parseInt(query.limit, 10) || 60));
  return { page, limit, skip: (page - 1) * limit };
}

exports.getProducts = async (req, res, next) => {
  try {
    const { page, limit, skip } = parsePagination(req.query);
    const filter = {};

    if (req.query.category) {
      filter.category = req.query.category;
    }

    const q = (req.query.search || '').trim();
    if (q) {
      filter.title = { $regex: escapeRegExp(q), $options: 'i' };
    }

    const isList = req.query.list === '1' || req.query.list === 'true';

    // List mode: only the fields a grid of product cards needs. Description,
    // video and extra images are dropped to keep the payload tiny. A generated
    // thumbnail is used when available, otherwise the first image is kept as
    // a fallback so the UI still renders on hosts without `sharp`.
    let select = null;
    if (isList) {
      select = {
        title: 1,
        price: 1,
        stock: 1,
        category: 1,
        imageUrl: 1,
        thumbnail: 1,
        images: { $slice: 1 },
      };
    }

    const [products, total] = await Promise.all([
      Product.find(filter)
        .select(select)
        .populate('category', 'name slug parent')
        .sort('-createdAt')
        .skip(skip)
        .limit(limit)
        .lean(),
      Product.countDocuments(filter),
    ]);

    if (isList) {
      await ensureThumbnails(products);
    }

    res.json({
      count: products.length,
      total,
      page,
      pages: Math.ceil(total / limit),
      products,
    });
  } catch (err) {
    next(err);
  }
};

exports.getProduct = async (req, res, next) => {
  try {
    const product = await Product.findById(req.params.id)
      .populate('category', 'name slug parent')
      .lean();
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
    // Images changed → drop the cached thumbnail so it gets regenerated.
    if (updateData.images) updateData.thumbnail = '';

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
