from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import sqlite3
from datetime import datetime
from fpdf import FPDF
import os
import io

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")


# ─── DB ───────────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                customer    TEXT    NOT NULL,
                product     TEXT    NOT NULL,
                price       REAL    NOT NULL,
                qty         INTEGER NOT NULL,
                subtotal    REAL    NOT NULL,
                tax_rate    REAL    NOT NULL DEFAULT 0,
                tax_amt     REAL    NOT NULL DEFAULT 0,
                grand_total REAL    NOT NULL,
                status      TEXT    NOT NULL DEFAULT 'unpaid',
                created_at  TEXT    NOT NULL
            )
        """)
        conn.commit()


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def validate_invoice_payload(data):
    errors = []
    for field in ("name", "product", "price", "qty"):
        if not data.get(field):
            errors.append(f"'{field}' is required")
    try:
        price = float(data.get("price", 0))
        if price < 0:
            errors.append("'price' must be >= 0")
    except (TypeError, ValueError):
        errors.append("'price' must be a number")
    try:
        qty = int(data.get("qty", 0))
        if qty <= 0:
            errors.append("'qty' must be > 0")
    except (TypeError, ValueError):
        errors.append("'qty' must be an integer")
    try:
        tax = float(data.get("tax", 0))
        if not (0 <= tax <= 100):
            errors.append("'tax' must be between 0 and 100")
    except (TypeError, ValueError):
        errors.append("'tax' must be a number")
    return errors


# ─── ROUTES ───────────────────────────────────────────────────────────────────

@app.route("/api/invoices", methods=["GET"])
def list_invoices():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM invoices ORDER BY created_at DESC"
        ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/invoices/<int:invoice_id>", methods=["GET"])
def get_invoice(invoice_id):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM invoices WHERE id = ?", (invoice_id,)
        ).fetchone()
    if not row:
        return jsonify({"error": "Invoice not found"}), 404
    return jsonify(dict(row))


@app.route("/api/invoices", methods=["POST"])
def create_invoice():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    errors = validate_invoice_payload(data)
    if errors:
        return jsonify({"errors": errors}), 422

    price    = float(data["price"])
    qty      = int(data["qty"])
    tax_rate = float(data.get("tax", 0))
    subtotal = round(price * qty, 2)
    tax_amt  = round(subtotal * tax_rate / 100, 2)
    grand    = round(subtotal + tax_amt, 2)
    now      = datetime.utcnow().isoformat()

    with get_db() as conn:
        cur = conn.execute("""
            INSERT INTO invoices
                (customer, product, price, qty, subtotal, tax_rate, tax_amt, grand_total, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'unpaid', ?)
        """, (data["name"], data["product"], price, qty, subtotal, tax_rate, tax_amt, grand, now))
        conn.commit()
        new_id = cur.lastrowid

    row = get_db().execute("SELECT * FROM invoices WHERE id = ?", (new_id,)).fetchone()
    return jsonify(dict(row)), 201


@app.route("/api/invoices/<int:invoice_id>/status", methods=["PATCH"])
def update_status(invoice_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in ("paid", "unpaid", "overdue"):
        return jsonify({"error": "status must be 'paid', 'unpaid', or 'overdue'"}), 422

    with get_db() as conn:
        result = conn.execute(
            "UPDATE invoices SET status = ? WHERE id = ?", (status, invoice_id)
        )
        conn.commit()
    if result.rowcount == 0:
        return jsonify({"error": "Invoice not found"}), 404
    return jsonify({"id": invoice_id, "status": status})


@app.route("/api/invoices/<int:invoice_id>", methods=["DELETE"])
def delete_invoice(invoice_id):
    with get_db() as conn:
        result = conn.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
        conn.commit()
    if result.rowcount == 0:
        return jsonify({"error": "Invoice not found"}), 404
    return "", 204


@app.route("/api/invoices/<int:invoice_id>/pdf", methods=["GET"])
def generate_pdf(invoice_id):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM invoices WHERE id = ?", (invoice_id,)
        ).fetchone()
    if not row:
        return jsonify({"error": "Invoice not found"}), 404

    inv = dict(row)

    pdf = FPDF()
    pdf.add_page()

    font_path = os.path.join(os.path.dirname(__file__), "DejaVuSans.ttf")
    font_bold_path = os.path.join(os.path.dirname(__file__), "DejaVuSans-Bold.ttf")
    if os.path.exists(font_path):
        pdf.add_font("DejaVu", "", font_path, uni=True)
        if os.path.exists(font_bold_path):
            pdf.add_font("DejaVu", "B", font_bold_path, uni=True)
        base_font = "DejaVu"
    else:
        base_font = "Helvetica"

    # ── Header ──────────────────────────────────────────────────────────────
    pdf.set_fill_color(15, 15, 15)
    pdf.rect(0, 0, 210, 40, "F")

    pdf.set_font(base_font, "B", 22)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(10, 12)
    pdf.cell(100, 12, "INVOICE", ln=False)

    pdf.set_font(base_font, "", 10)
    pdf.set_text_color(180, 180, 180)
    pdf.set_xy(130, 14)
    pdf.cell(70, 6, f"Invoice #{str(inv['id']).zfill(4)}", align="R", ln=True)
    pdf.set_xy(130, 20)
    pdf.cell(70, 6, inv["created_at"][:10], align="R", ln=True)

    # ── Bill To ─────────────────────────────────────────────────────────────
    pdf.set_text_color(0, 0, 0)
    pdf.set_xy(10, 50)
    pdf.set_font(base_font, "", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 5, "BILL TO", ln=True)

    pdf.set_xy(10, 56)
    pdf.set_font(base_font, "B", 13)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 7, inv["customer"], ln=True)

    # ── Status badge ────────────────────────────────────────────────────────
    status_colors = {
        "paid":    (220, 252, 231),
        "unpaid":  (254, 249, 195),
        "overdue": (254, 226, 226),
    }
    status_text_colors = {
        "paid":    (21, 128, 61),
        "unpaid":  (133, 79, 11),
        "overdue": (185, 28, 28),
    }
    bg = status_colors.get(inv["status"], (240, 240, 240))
    fg = status_text_colors.get(inv["status"], (80, 80, 80))
    pdf.set_fill_color(*bg)
    pdf.set_text_color(*fg)
    pdf.set_font(base_font, "B", 9)
    pdf.set_xy(155, 50)
    pdf.cell(45, 7, inv["status"].upper(), align="C", fill=True, ln=True)

    # ── Items table header ───────────────────────────────────────────────────
    pdf.set_xy(10, 80)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_text_color(60, 60, 60)
    pdf.set_font(base_font, "B", 9)
    col_w = [90, 25, 30, 30]
    headers = ["DESCRIPTION", "QTY", "UNIT PRICE", "AMOUNT"]
    for h, w in zip(headers, col_w):
        pdf.cell(w, 8, h, fill=True, border=0)
    pdf.ln()

    # ── Items row ────────────────────────────────────────────────────────────
    pdf.set_text_color(0, 0, 0)
    pdf.set_font(base_font, "", 10)
    pdf.set_xy(10, pdf.get_y())
    pdf.cell(col_w[0], 9, inv["product"])
    pdf.cell(col_w[1], 9, str(inv["qty"]))
    pdf.cell(col_w[2], 9, f"\u20b9{inv['price']:,.2f}")
    pdf.cell(col_w[3], 9, f"\u20b9{inv['subtotal']:,.2f}")
    pdf.ln()

    # ── Divider ──────────────────────────────────────────────────────────────
    y = pdf.get_y() + 4
    pdf.set_draw_color(220, 220, 220)
    pdf.line(10, y, 200, y)

    # ── Totals ───────────────────────────────────────────────────────────────
    def total_row(label, value, bold=False):
        pdf.set_xy(130, pdf.get_y() + 5)
        pdf.set_font(base_font, "B" if bold else "", 10)
        pdf.set_text_color(80, 80, 80) if not bold else pdf.set_text_color(0, 0, 0)
        pdf.cell(35, 6, label)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(35, 6, f"\u20b9{value:,.2f}", align="R")
        pdf.ln()

    pdf.set_y(y + 4)
    total_row("Subtotal", inv["subtotal"])
    total_row(f"Tax ({inv['tax_rate']:.0f}%)", inv["tax_amt"])

    pdf.set_xy(10, pdf.get_y())
    pdf.set_fill_color(15, 15, 15)
    pdf.rect(130, pdf.get_y() + 3, 70, 10, "F")
    pdf.set_xy(130, pdf.get_y() + 3)
    pdf.set_font(base_font, "B", 11)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(35, 10, "Total")
    pdf.cell(35, 10, f"\u20b9{inv['grand_total']:,.2f}", align="R")

    # ── Footer ───────────────────────────────────────────────────────────────
    pdf.set_y(270)
    pdf.set_font(base_font, "", 8)
    pdf.set_text_color(160, 160, 160)
    pdf.cell(0, 5, "Thank you for your business.", align="C")

    buf = io.BytesIO(pdf.output())
    buf.seek(0)
    return send_file(
        buf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"invoice_{str(invoice_id).zfill(4)}.pdf",
    )


@app.route("/api/stats", methods=["GET"])
def stats():
    with get_db() as conn:
        row = conn.execute("""
            SELECT
                COUNT(*)                                        AS total,
                COALESCE(SUM(grand_total), 0)                  AS revenue,
                COALESCE(SUM(CASE WHEN status='paid'    THEN grand_total END), 0) AS paid,
                COALESCE(SUM(CASE WHEN status='unpaid'  THEN grand_total END), 0) AS unpaid,
                COALESCE(SUM(CASE WHEN status='overdue' THEN grand_total END), 0) AS overdue,
                COUNT(CASE WHEN status='paid' THEN 1 END)      AS paid_count,
                COUNT(CASE WHEN status='unpaid' THEN 1 END)    AS unpaid_count,
                COUNT(CASE WHEN status='overdue' THEN 1 END)   AS overdue_count
            FROM invoices
        """).fetchone()
    return jsonify(dict(row))


# ─── ENTRY ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
