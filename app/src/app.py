import logging
import os
import socket
import sys
import time
from datetime import date
from decimal import Decimal, InvalidOperation
from importlib.metadata import version as package_version

import psycopg
from flask import Flask, abort, g, jsonify, redirect, render_template, request, url_for
from psycopg.rows import dict_row

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer     TEXT          NOT NULL,
    item         TEXT          NOT NULL,
    amount       NUMERIC(10,2) NOT NULL CHECK (amount >= 0),
    created_at   DATE          NOT NULL DEFAULT CURRENT_DATE,
    fulfilled    BOOLEAN       NOT NULL DEFAULT FALSE,
    fulfilled_at DATE
);
"""

DEMO_ORDERS = [
    ("Anna Kowalska", "Standing desk", Decimal("1290.00"), date(2026, 10, 1), True),
    ("Piotr Nowak", "Monitor arm", Decimal("249.90"), date(2026, 10, 2), True),
    ("Studio Lumen", "Office chair x4", Decimal("3960.00"), date(2026, 10, 4), False),
    ("Marta Zielinska", "Desk lamp", Decimal("119.00"), date(2026, 10, 6), False),
    ("Jan Wisniewski", "Cable tray", Decimal("79.50"), date(2026, 10, 7), False),
]

STATUSES = ("all", "open", "fulfilled")
MAX_AMOUNT = Decimal("99999999.99")

log = logging.getLogger("dashboard")


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        DATABASE_URL=os.environ.get("DATABASE_URL", ""),
        APP_VERSION=os.environ.get("APP_VERSION", "dev"),
        SEED_DEMO_DATA=os.environ.get("SEED_DEMO_DATA", "1") == "1",
    )
    if config:
        app.config.update(config)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    init_db(app)

    @app.template_filter("money")
    def money(value):
        return f"{value:,.2f} PLN".replace(",", " ")

    def get_db():
        if "db" not in g:
            g.db = psycopg.connect(
                app.config["DATABASE_URL"], row_factory=dict_row, connect_timeout=5
            )
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def counts():
        return get_db().execute(
            """SELECT COUNT(*)                                       AS total,
                      COUNT(*) FILTER (WHERE NOT fulfilled)          AS open,
                      COUNT(*) FILTER (WHERE fulfilled)              AS fulfilled,
                      COALESCE(SUM(amount) FILTER (WHERE fulfilled), 0) AS revenue
               FROM orders"""
        ).fetchone()

    @app.get("/")
    def overview():
        latest = get_db().execute(
            "SELECT * FROM orders ORDER BY id DESC LIMIT 5"
        ).fetchall()
        return render_template("overview.html", stats=counts(), latest=latest)

    @app.get("/orders")
    def orders():
        status = request.args.get("status", "all")
        if status not in STATUSES:
            abort(404)
        return render_orders(status)

    def render_orders(status, error=None, form=None):
        query = "SELECT * FROM orders"
        if status == "open":
            query += " WHERE NOT fulfilled"
        elif status == "fulfilled":
            query += " WHERE fulfilled"
        query += " ORDER BY id DESC"
        rows = get_db().execute(query).fetchall()
        return render_template(
            "orders.html",
            rows=rows,
            status=status,
            stats=counts(),
            error=error,
            form=form or {},
        )

    def parse_order_form(form):
        customer = form.get("customer", "").strip()
        item = form.get("item", "").strip()
        raw_amount = form.get("amount", "").strip().replace(",", ".")
        try:
            amount = Decimal(raw_amount).quantize(Decimal("0.01"))
            if not (Decimal("0") <= amount <= MAX_AMOUNT):
                raise InvalidOperation
        except InvalidOperation:
            amount = None

        if not customer or not item or amount is None:
            return None
        return customer, item, amount

    @app.post("/orders")
    def create_order():
        order_data = parse_order_form(request.form)
        if order_data is None:
            log.warning("order rejected: invalid form data")
            return (
                render_orders(
                    "all",
                    error="Enter a customer, an item and an amount of 0 or more.",
                    form=request.form,
                ),
                400,
            )

        customer, item, amount = order_data
        db = get_db()
        row = db.execute(
            "INSERT INTO orders (customer, item, amount) VALUES (%s, %s, %s) RETURNING id",
            (customer, item, amount),
        ).fetchone()
        db.commit()
        log.info("order created id=%s customer=%r amount=%s", row["id"], customer, amount)
        return redirect(url_for("orders", status="open"))

    @app.get("/orders/<int:order_id>/edit")
    def edit_order(order_id):
        row = get_db().execute(
            "SELECT id, customer, item, amount FROM orders WHERE id = %s",
            (order_id,),
        ).fetchone()
        if row is None:
            abort(404)
        status = request.args.get("status", "all")
        if status not in STATUSES:
            status = "all"
        return render_template("edit_order.html", order=row, status=status, error=None, form={})

    @app.post("/orders/<int:order_id>/edit")
    def update_order(order_id):
        db = get_db()
        row = db.execute(
            "SELECT id, customer, item, amount FROM orders WHERE id = %s",
            (order_id,),
        ).fetchone()
        if row is None:
            abort(404)

        order_data = parse_order_form(request.form)
        status = request.form.get("status", "all")
        if status not in STATUSES:
            status = "all"
        if order_data is None:
            log.warning("order update rejected: invalid form data id=%s", order_id)
            return (
                render_template(
                    "edit_order.html",
                    order=row,
                    status=status,
                    error="Enter a customer, an item and an amount of 0 or more.",
                    form=request.form,
                ),
                400,
            )

        customer, item, amount = order_data
        db.execute(
            "UPDATE orders SET customer = %s, item = %s, amount = %s WHERE id = %s",
            (customer, item, amount, order_id),
        )
        db.commit()
        log.info("order updated id=%s customer=%r amount=%s", order_id, customer, amount)
        return redirect(url_for("orders", status=status))

    @app.post("/orders/<int:order_id>/delete")
    def delete_order(order_id):
        db = get_db()
        row = db.execute(
            "DELETE FROM orders WHERE id = %s RETURNING id", (order_id,)
        ).fetchone()
        if row is None:
            log.warning("delete failed: order id=%s not found", order_id)
            abort(404)
        db.commit()
        log.info("order deleted id=%s", order_id)
        status = request.form.get("status", "all")
        return redirect(url_for("orders", status=status if status in STATUSES else "all"))

    @app.post("/orders/<int:order_id>/toggle")
    def toggle_order(order_id):
        db = get_db()
        row = db.execute(
            "SELECT fulfilled FROM orders WHERE id = %s", (order_id,)
        ).fetchone()
        if row is None:
            log.warning("toggle failed: order id=%s not found", order_id)
            abort(404)
        if row["fulfilled"]:
            db.execute(
                "UPDATE orders SET fulfilled = FALSE, fulfilled_at = NULL WHERE id = %s",
                (order_id,),
            )
            log.info("order reopened id=%s", order_id)
        else:
            db.execute(
                "UPDATE orders SET fulfilled = TRUE, fulfilled_at = CURRENT_DATE WHERE id = %s",
                (order_id,),
            )
            log.info("order fulfilled id=%s", order_id)
        db.commit()
        status = request.form.get("status", "all")
        return redirect(url_for("orders", status=status if status in STATUSES else "all"))

    @app.get("/about")
    def about():
        db = get_db()
        version = db.execute("SHOW server_version").fetchone()["server_version"]
        size = db.execute(
            "SELECT pg_database_size(current_database()) AS size"
        ).fetchone()["size"]
        return render_template(
            "about.html",
            version=app.config["APP_VERSION"],
            build_commit=app.config["APP_VERSION"].removeprefix("sha-"),
            hostname=socket.gethostname(),
            python_version=sys.version.split()[0],
            flask_version=package_version("Flask"),
            db_host=db.info.host,
            db_name=db.info.dbname,
            db_version=version,
            db_size_mb=round(size / 1024 / 1024, 1),
        )

    @app.get("/health")
    def health():
        try:
            get_db().execute("SELECT 1").fetchone()
        except psycopg.Error:
            log.exception("health check failed: database unavailable")
            return jsonify(status="error", database="unavailable"), 503
        return jsonify(status="ok", version=app.config["APP_VERSION"])

    return app


def init_db(app, attempts=30, delay=2):
    """Wait for PostgreSQL, create the schema, optionally seed demo data."""
    url = app.config["DATABASE_URL"]
    if not url:
        raise RuntimeError("DATABASE_URL is not set")

    for attempt in range(1, attempts + 1):
        try:
            conn = psycopg.connect(url, connect_timeout=3)
            break
        except psycopg.OperationalError as exc:
            log.warning("database not ready (attempt %d/%d): %s", attempt, attempts, exc)
            time.sleep(delay)
    else:
        raise RuntimeError("database did not become available")

    with conn:
        conn.execute(SCHEMA)
        empty = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0
        if empty and app.config["SEED_DEMO_DATA"]:
            for customer, item, amount, created, done in DEMO_ORDERS:
                conn.execute(
                    "INSERT INTO orders (customer, item, amount, created_at, fulfilled, fulfilled_at)"
                    " VALUES (%s, %s, %s, %s, %s, %s)",
                    (customer, item, amount, created, done, created if done else None),
                )
            log.info("database seeded with %d demo orders", len(DEMO_ORDERS))
    conn.close()
    log.info("database ready")


app = create_app() if os.environ.get("FLASK_SKIP_AUTOCREATE") != "1" else None
