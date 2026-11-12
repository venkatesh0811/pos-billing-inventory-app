"""Simple POS Billing & Inventory app (Flask + SQLite)."""
import sqlite3
from datetime import datetime
from flask import Flask, g, render_template, request, redirect, url_for, jsonify, flash, abort

app = Flask(__name__)
app.secret_key = "change-this-secret"   # needed for flash messages
DB = "pos.db"
LOW_STOCK = 5                            # stock at or below this is "low"


# ---------- Database helpers ----------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db:
        db.close()


def init_db():
    db = sqlite3.connect(DB)
    db.executescript("""
    CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        price REAL NOT NULL CHECK(price >= 0),
        stock INTEGER NOT NULL CHECK(stock >= 0));
    CREATE TABLE IF NOT EXISTS invoices(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        total REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS invoice_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER NOT NULL REFERENCES invoices(id),
        product_id INTEGER NOT NULL REFERENCES products(id),
        qty INTEGER NOT NULL,
        price REAL NOT NULL);
    """)
    db.commit()
    db.close()


# ---------- Pages: inventory ----------
@app.route("/")
def home():
    return redirect(url_for("products"))


@app.route("/products")
def products():
    rows = get_db().execute("SELECT * FROM products ORDER BY name").fetchall()
    return render_template("products.html", products=rows, low=LOW_STOCK)


@app.route("/products/add", methods=["POST"])
def add_product():
    name = request.form.get("name", "").strip()
    try:
        price = float(request.form["price"])
        stock = int(request.form["stock"])
        if not name or price < 0 or stock < 0:
            raise ValueError
    except (KeyError, ValueError):
        flash("Enter a valid name, price and stock.", "error")
        return redirect(url_for("products"))
    try:
        db = get_db()
        db.execute("INSERT INTO products(name, price, stock) VALUES (?,?,?)", (name, price, stock))
        db.commit()
        flash(f"Added {name}.", "ok")
    except sqlite3.IntegrityError:
        flash("A product with that name already exists.", "error")
    return redirect(url_for("products"))


@app.route("/products/<int:pid>/restock", methods=["POST"])
def restock(pid):
    try:
        qty = int(request.form["qty"])
        if qty <= 0:
            raise ValueError
    except (KeyError, ValueError):
        flash("Enter a valid quantity.", "error")
        return redirect(url_for("products"))
    db = get_db()
    db.execute("UPDATE products SET stock = stock + ? WHERE id = ?", (qty, pid))
    db.commit()
    flash("Stock updated.", "ok")
    return redirect(url_for("products"))


@app.route("/products/<int:pid>/delete", methods=["POST"])
def delete_product(pid):
    db = get_db()
    used = db.execute("SELECT 1 FROM invoice_items WHERE product_id=?", (pid,)).fetchone()
    if used:
        flash("Cannot delete a product that is on past invoices.", "error")
    else:
        db.execute("DELETE FROM products WHERE id=?", (pid,))
        db.commit()
        flash("Product deleted.", "ok")
    return redirect(url_for("products"))


# ---------- Billing: page + JSON API ----------
@app.route("/billing")
def billing():
    return render_template("billing.html")


@app.route("/api/products")
def api_products():
    rows = get_db().execute("SELECT id, name, price, stock FROM products WHERE stock > 0 ORDER BY name").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/invoices", methods=["POST"])
def api_create_invoice():
    """Body: {"items": [{"product_id": 1, "qty": 2}, ...]}"""
    data = request.get_json(silent=True) or {}
    items = data.get("items", [])
    if not items:
        return jsonify(error="Cart is empty."), 400

    db = get_db()
    lines, total = [], 0.0
    for it in items:
        try:
            pid, qty = int(it["product_id"]), int(it["qty"])
        except (KeyError, ValueError, TypeError):
            return jsonify(error="Invalid item."), 400
        if qty <= 0:
            return jsonify(error="Quantity must be at least 1."), 400
        p = db.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
        if not p:
            return jsonify(error=f"Product {pid} not found."), 404
        if p["stock"] < qty:
            return jsonify(error=f"Only {p['stock']} of {p['name']} in stock."), 400
        lines.append((p["id"], qty, p["price"]))
        total += qty * p["price"]

    cur = db.execute("INSERT INTO invoices(created_at, total) VALUES (?,?)",
                     (datetime.now().strftime("%Y-%m-%d %H:%M"), round(total, 2)))
    inv_id = cur.lastrowid
    for pid, qty, price in lines:
        db.execute("INSERT INTO invoice_items(invoice_id, product_id, qty, price) VALUES (?,?,?,?)",
                   (inv_id, pid, qty, price))
        db.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (qty, pid))  # auto stock update
    db.commit()
    return jsonify(invoice_id=inv_id, total=round(total, 2)), 201


# ---------- Invoices ----------
@app.route("/invoices")
def invoices():
    rows = get_db().execute("SELECT * FROM invoices ORDER BY id DESC").fetchall()
    return render_template("invoices.html", invoices=rows)


@app.route("/invoices/<int:iid>")
def invoice_detail(iid):
    db = get_db()
    inv = db.execute("SELECT * FROM invoices WHERE id=?", (iid,)).fetchone()
    if not inv:
        abort(404)
    items = db.execute("""SELECT p.name, ii.qty, ii.price, ii.qty*ii.price AS line_total
                          FROM invoice_items ii JOIN products p ON p.id = ii.product_id
                          WHERE ii.invoice_id = ?""", (iid,)).fetchall()
    return render_template("invoice_detail.html", inv=inv, items=items)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
