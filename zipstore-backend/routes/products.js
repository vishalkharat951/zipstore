const express = require('express');
const router = express.Router();
const productController = require('../controllers/productController');
const categoryController = require('../controllers/categoryController');
const { authenticate, isAdmin } = require('../middleware/auth');

router.get('/products', productController.getProducts);
router.get('/products/:id', productController.getProduct);
router.post('/products', authenticate, isAdmin, productController.createProduct);
router.put('/products/:id', authenticate, isAdmin, productController.updateProduct);
router.delete('/products/:id', authenticate, isAdmin, productController.deleteProduct);

router.get('/categories', categoryController.getCategories);
router.get('/categories/:id', categoryController.getCategory);
router.post('/categories', authenticate, isAdmin, categoryController.createCategory);
router.put('/categories/:id', authenticate, isAdmin, categoryController.updateCategory);
router.delete('/categories/:id', authenticate, isAdmin, categoryController.deleteCategory);

module.exports = router;
