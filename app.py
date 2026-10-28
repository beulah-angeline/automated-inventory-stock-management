from flask import Flask, render_template, request, redirect, url_for, flash, Response
import sqlite3, csv, io, os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "change-this-demo-secret"
DB_PATH = os.path.join(os.path.dirname(__file__), "inventory.db")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT DEFAULT '',
            quantity INTEGER NOT NULL DEFAULT 0,
            min_stock INTEGER NOT NULL DEFAULT 5,
            unit_price REAL NOT NULL DEFAULT 0,
            supplier TEXT DEFAULT ''
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            note TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(product_id) REFERENCES products(id)
        )""")
        count = con.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if count == 0:
            con.executemany(
                "INSERT INTO products(name,category,quantity,min_stock,unit_price,supplier) VALUES(?,?,?,?,?,?)",
                [
                    ("Notebook", "Stationery", 30, 10, 45.0, "ABC Suppliers"),
                    ("Pen", "Stationery", 8, 15, 10.0, "WriteWell"),
                    ("USB Drive", "Electronics", 0, 5, 350.0, "Tech Mart"),
                    ("File Folder", "Office", 22, 8, 25.0, "ABC Suppliers"),
                ],
            )

def stock_status(product):
    if product["quantity"] <= 0:
        return "Out of stock"
    if product["quantity"] <= product["min_stock"]:
        return "Low stock"
    return "In stock"

@app.route("/")
def dashboard():
    with db() as con:
        products = con.execute("SELECT * FROM products ORDER BY name").fetchall()
        total_products = len(products)
        low = [p for p in products if p["quantity"] > 0 and p["quantity"] <= p["min_stock"]]
        out = [p for p in products if p["quantity"] <= 0]
        total_value = sum(p["quantity"] * p["unit_price"] for p in products)
        recent = con.execute("""SELECT t.*, p.name AS product_name FROM transactions t
                              JOIN products p ON p.id=t.product_id
                              ORDER BY t.id DESC LIMIT 8""").fetchall()
    return render_template("dashboard.html", products=products, total_products=total_products,
                           low_count=len(low), out_count=len(out), total_value=total_value, recent=recent,
                           status=stock_status)

@app.route("/products")
def products():
    q = request.args.get("q", "").strip()
    with db() as con:
        if q:
            rows = con.execute("SELECT * FROM products WHERE name LIKE ? OR category LIKE ? ORDER BY name",
                               (f"%{q}%", f"%{q}%")).fetchall()
        else:
            rows = con.execute("SELECT * FROM products ORDER BY name").fetchall()
    return render_template("products.html", products=rows, q=q, status=stock_status)

@app.route("/products/add", methods=["GET", "POST"])
def add_product():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        try:
            quantity = int(request.form.get("quantity", "0"))
            min_stock = int(request.form.get("min_stock", "5"))
            price = float(request.form.get("unit_price", "0"))
            if not name or quantity < 0 or min_stock < 0 or price < 0:
                raise ValueError
        except ValueError:
            flash("Enter a product name and valid non-negative numeric values.", "error")
            return render_template("product_form.html", product=request.form, title="Add product")
        with db() as con:
            con.execute("INSERT INTO products(name,category,quantity,min_stock,unit_price,supplier) VALUES(?,?,?,?,?,?)",
                        (name, request.form.get("category","").strip(), quantity, min_stock, price,
                         request.form.get("supplier","").strip()))
        flash("Product added successfully.", "success")
        return redirect(url_for("products"))
    return render_template("product_form.html", product={}, title="Add product")

@app.route("/products/<int:pid>/edit", methods=["GET", "POST"])
def edit_product(pid):
    with db() as con:
        product = con.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
        if not product:
            flash("Product not found.", "error")
            return redirect(url_for("products"))
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            try:
                quantity = int(request.form.get("quantity", "0"))
                min_stock = int(request.form.get("min_stock", "5"))
                price = float(request.form.get("unit_price", "0"))
                if not name or quantity < 0 or min_stock < 0 or price < 0:
                    raise ValueError
            except ValueError:
                flash("Enter valid non-negative values.", "error")
                return render_template("product_form.html", product=request.form, title="Edit product")
            con.execute("""UPDATE products SET name=?, category=?, quantity=?, min_stock=?, unit_price=?, supplier=?
                           WHERE id=?""",
                        (name, request.form.get("category","").strip(), quantity, min_stock, price,
                         request.form.get("supplier","").strip(), pid))
            flash("Product updated successfully.", "success")
            return redirect(url_for("products"))
    return render_template("product_form.html", product=product, title="Edit product")

@app.route("/products/<int:pid>/delete", methods=["POST"])
def delete_product(pid):
    with db() as con:
        con.execute("DELETE FROM transactions WHERE product_id=?", (pid,))
        con.execute("DELETE FROM products WHERE id=?", (pid,))
    flash("Product deleted.", "success")
    return redirect(url_for("products"))

@app.route("/transactions", methods=["GET", "POST"])
def transactions():
    with db() as con:
        if request.method == "POST":
            try:
                pid = int(request.form["product_id"])
                qty = int(request.form["quantity"])
                action = request.form["action"]
                if qty <= 0 or action not in ("Stock In", "Stock Out"):
                    raise ValueError
            except (ValueError, KeyError):
                flash("Choose a product and enter a quantity greater than zero.", "error")
                return redirect(url_for("transactions"))
            product = con.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
            if not product:
                flash("Product not found.", "error")
                return redirect(url_for("transactions"))
            new_qty = product["quantity"] + qty if action == "Stock In" else product["quantity"] - qty
            if new_qty < 0:
                flash("Stock Out quantity cannot exceed available stock.", "error")
                return redirect(url_for("transactions"))
            con.execute("UPDATE products SET quantity=? WHERE id=?", (new_qty, pid))
            con.execute("INSERT INTO transactions(product_id,action,quantity,note,created_at) VALUES(?,?,?,?,?)",
                        (pid, action, qty, request.form.get("note","").strip(), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            flash(f"{action} recorded successfully.", "success")
            return redirect(url_for("transactions"))
        products = con.execute("SELECT * FROM products ORDER BY name").fetchall()
        rows = con.execute("""SELECT t.*, p.name AS product_name FROM transactions t
                            JOIN products p ON p.id=t.product_id ORDER BY t.id DESC LIMIT 100""").fetchall()
    return render_template("transactions.html", products=products, transactions=rows)

@app.route("/reports")
def reports():
    with db() as con:
        rows = con.execute("SELECT * FROM products ORDER BY name").fetchall()
        transactions_count = con.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    return render_template("reports.html", products=rows, status=stock_status, transactions_count=transactions_count)

@app.route("/export/products.csv")
def export_products():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID","Product","Category","Quantity","Minimum Stock","Unit Price","Supplier","Status","Stock Value"])
    with db() as con:
        for p in con.execute("SELECT * FROM products ORDER BY name"):
            writer.writerow([p["id"], p["name"], p["category"], p["quantity"], p["min_stock"], p["unit_price"],
                             p["supplier"], stock_status(p), p["quantity"] * p["unit_price"]])
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition":"attachment; filename=inventory_report.csv"})

@app.route("/export/transactions.csv")
def export_transactions():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Transaction ID","Product","Action","Quantity","Note","Date"])
    with db() as con:
        rows = con.execute("""SELECT t.*, p.name AS product_name FROM transactions t
                            JOIN products p ON p.id=t.product_id ORDER BY t.id DESC""")
        for r in rows:
            writer.writerow([r["id"],r["product_name"],r["action"],r["quantity"],r["note"],r["created_at"]])
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition":"attachment; filename=transaction_report.csv"})

@app.errorhandler(404)
def not_found(_):
    return render_template("404.html"), 404

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
