# Zip Store

A full-featured e-commerce web application built with Django. Browse products, manage a shopping cart, place orders, and pay via PhonePe payment gateway.

## Features

- **Product Catalog** — Categories, product listings with search/filter, discount pricing, product images and videos
- **Shopping Cart** — Session-based for guests, database-backed for logged-in users, automatic cart merge on login
- **Order Management** — Full checkout flow, order status workflow (Pending → Confirmed → Packed → Shipped → Delivered / Cancelled), stock management
- **PhonePe Payments** — Fully integrated UPI-based payment gateway with UAT sandbox & production environments
- **User Accounts** — Registration, login/profile management, address book, order history dashboard
- **Admin Panel** — Customized Django admin with dashboard statistics

## Tech Stack

- **Framework:** Django 6.0+
- **Frontend:** Bootstrap 5, Bootstrap Icons
- **Database:** SQLite (dev) / PostgreSQL (production)
- **WSGI Server:** Gunicorn
- **Static Files:** WhiteNoise
- **Payment Gateway:** PhonePe API

## Getting Started

1. Clone the repo:
   ```bash
   git clone https://github.com/vishalkharat951/zipstore.github.io.git
   cd zipstore.github.io
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/macOS
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables — copy `.env.example` to `.env` and fill in values.

5. Run migrations:
   ```bash
   python manage.py migrate
   ```

6. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

7. Run the development server:
   ```bash
   python manage.py runserver
   ```

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for a full deployment checklist.

## License

MIT
