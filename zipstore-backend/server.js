const express = require('express');
const mongoose = require('mongoose');
const compression = require('compression');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
require('dotenv').config();

const authRoutes = require('./routes/auth');
const productRoutes = require('./routes/products');
const orderRoutes = require('./routes/orders');

const app = express();
const PORT = process.env.PORT || 5000;

const pluginsDir = path.join(__dirname, 'plugins');
if (fs.existsSync(pluginsDir)) {
  const pluginFiles = fs.readdirSync(pluginsDir).filter(f => f.endsWith('.js'));
  for (const file of pluginFiles) {
    const plugin = require(path.join(pluginsDir, file));
    if (typeof plugin === 'function') {
      plugin(app);
      console.log(`Plugin loaded: ${file}`);
    }
  }
}

const allowedOrigins = (process.env.ALLOWED_ORIGINS || 'https://vishalkharat951.github.io,http://localhost:3000,http://localhost:5173').split(',');

app.use(cors({
  origin: function (origin, callback) {
    if (!origin || allowedOrigins.indexOf(origin) !== -1 || process.env.NODE_ENV === 'development') {
      callback(null, true);
    } else {
      callback(new Error('Not allowed by CORS'));
    }
  },
  credentials: true,
}));

app.options('*', cors());

app.use(compression());
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

app.use('/api/auth', authRoutes);
app.use('/api', productRoutes);
app.use('/api', orderRoutes);

app.get('/api/health', (req, res) => {
  res.json({ status: 'OK', timestamp: new Date().toISOString() });
});

app.use('/api', (req, res) => {
  res.status(404).json({ error: `API endpoint not found: ${req.method} ${req.originalUrl}` });
});

app.use((err, req, res, next) => {
  console.error('Unhandled error:', err.stack);

  if (err.message === 'Not allowed by CORS') {
    return res.status(403).json({ error: 'CORS request rejected' });
  }

  res.status(err.status || 500).json({
    error: err.message || 'Internal Server Error',
  });
});

const MONGODB_URI = process.env.MONGODB_URI;
if (!MONGODB_URI) {
  console.error('FATAL: MONGODB_URI environment variable is not set');
  process.exit(1);
}

mongoose
  .connect(MONGODB_URI, {
    serverSelectionTimeoutMS: 15000,
    socketTimeoutMS: 45000,
  })
  .then(() => {
    console.log('Connected to MongoDB');
    app.listen(PORT, '0.0.0.0', () => {
      console.log(`ZipStore API running on port ${PORT}`);
    });
  })
  .catch((err) => {
    console.error('MongoDB connection error:', err.name, err.message);
    if (err.name === 'MongooseServerSelectionError') {
      console.error('Check that your MongoDB Atlas IP whitelist includes 0.0.0.0/0');
    }
    process.exit(1);
  });

module.exports = app;
