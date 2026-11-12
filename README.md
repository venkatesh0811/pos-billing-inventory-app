# Simple POS Billing & Inventory App

A small full-stack web app: manage products and stock, create bills, auto-reduce stock, view invoices.

**Tech:** Python, Flask, SQLite, HTML, CSS, JavaScript (fetch API)

## Run it
1. Install Python 3.9+
2. In this folder: `pip install -r requirements.txt`
3. `python app.py`
4. Open http://127.0.0.1:5000

## Features
- Inventory: add product, restock, delete, low-stock highlight (stock <= 5)
- Billing: pick products, build a cart, generate an invoice (JavaScript calls the REST API)
- Stock is reduced automatically when an invoice is saved
- Invoices list, invoice detail page, print button
- Validation: no empty cart, no negative values, no selling more than the stock

## How it works (learn this before an interview)
- `app.py` is the back end. Routes return HTML pages; `/api/products` and `/api/invoices` return/accept JSON (REST API).
- Database has 3 tables: `products`, `invoices`, `invoice_items` (one invoice has many items).
- `POST /api/invoices` checks stock for every item, saves the invoice and its items, then reduces stock.
- `templates/` holds the pages (Jinja2). `billing.html` has the JavaScript that keeps the cart and calls the API.
- `static/style.css` is the styling.

## Questions you should be able to answer
1. What is the difference between a normal route and an API route here?
2. Why is there an `invoice_items` table instead of storing items inside `invoices`?
3. What stops a user from selling more stock than exists? (Check it in both the browser and the server.)
4. Why use `?` placeholders in SQL? (Prevents SQL injection.)
5. What would you add next? (Login, GST, search, sales report, MySQL instead of SQLite.)

## Ideas to extend it (and update your resume)
Login with roles, daily sales report, search, barcode field, MySQL.
