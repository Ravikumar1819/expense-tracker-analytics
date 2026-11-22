import calendar
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from flask import abort, render_template, request, session
from common import create_base, data, db, install_auth, login_required, pagination, text


def month_range(value):
    if not re.fullmatch(r"\d{4}-\d{2}", value or ""):
        abort(400, "Month must use YYYY-MM.")
    try:
        year, month = map(int, value.split("-"))
        return date(year,month,1).isoformat(), date(year,month,calendar.monthrange(year,month)[1]).isoformat()
    except ValueError:
        abort(400, "Choose a valid month.")


def create_app(config=None):
    app = create_base(config)
    install_auth(app)
    with app.app_context():
        db().executescript("""
        CREATE TABLE IF NOT EXISTS transactions(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), kind TEXT NOT NULL CHECK(kind IN ('income','expense')), amount_cents INTEGER NOT NULL CHECK(amount_cents > 0), category TEXT NOT NULL, note TEXT NOT NULL, occurred_on TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS transactions_user_date ON transactions(user_id,occurred_on);
        """)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/transactions")
    @login_required
    def transactions():
        start,end = month_range(request.args.get("month", date.today().strftime("%Y-%m")))
        page,limit = pagination()
        args = (session["user_id"],start,end)
        where = "user_id=? AND occurred_on BETWEEN ? AND ?"
        total = db().execute(f"SELECT count(*) FROM transactions WHERE {where}",args).fetchone()[0]
        rows = db().execute(f"SELECT * FROM transactions WHERE {where} ORDER BY occurred_on DESC,id DESC LIMIT ? OFFSET ?",(*args,limit,(page-1)*limit)).fetchall()
        return {"items": [dict(r) for r in rows], "total": total,"page":page,"limit":limit}

    @app.get("/api/summary")
    @login_required
    def summary():
        start,end = month_range(request.args.get("month", date.today().strftime("%Y-%m")))
        rows = db().execute("SELECT kind,category,SUM(amount_cents) AS cents FROM transactions WHERE user_id=? AND occurred_on BETWEEN ? AND ? GROUP BY kind,category ORDER BY cents DESC", (session["user_id"],start,end)).fetchall()
        income = sum(r["cents"] for r in rows if r["kind"] == "income")
        expense = sum(r["cents"] for r in rows if r["kind"] == "expense")
        return {"income_cents":income,"expense_cents":expense,"balance_cents":income-expense,"categories":[{"category":r["category"],"cents":r["cents"]} for r in rows if r["kind"] == "expense"]}

    @app.route("/api/transactions",methods=["POST"])
    @app.route("/api/transactions/<int:record_id>",methods=["PUT","DELETE"])
    @login_required
    def save(record_id=None):
        if record_id and not db().execute("SELECT id FROM transactions WHERE id=? AND user_id=?", (record_id,session["user_id"])).fetchone():
            abort(404, "Transaction not found.")
        if request.method == "DELETE":
            db().execute("DELETE FROM transactions WHERE id=? AND user_id=?",(record_id,session["user_id"]))
        else:
            p = data()
            if not isinstance(p.get("kind"), str) or p["kind"] not in {"income","expense"}:
                abort(400, "Choose income or expense.")
            try:
                amount = Decimal(str(p.get("amount")))
                if not amount.is_finite() or amount <= 0 or amount > 100000000 or amount.as_tuple().exponent < -2:
                    raise InvalidOperation
                cents = int(amount * 100)
            except (InvalidOperation,ValueError,TypeError):
                abort(400, "Amount must be positive with at most two decimal places (maximum 100000000).")
            occurred = p.get("occurred_on")
            try:
                if not isinstance(occurred,str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",occurred):
                    raise ValueError
                date.fromisoformat(occurred)
            except (ValueError,TypeError):
                abort(400, "Date must use YYYY-MM-DD.")
            note = p.get("note", "")
            if not isinstance(note,str) or len(note) > 300:
                abort(400, "Note must be at most 300 characters.")
            values = (p["kind"],cents,text(p.get("category"),"Category",60),note.strip(),occurred)
            if record_id:
                db().execute("UPDATE transactions SET kind=?,amount_cents=?,category=?,note=?,occurred_on=? WHERE id=? AND user_id=?",(*values,record_id,session["user_id"]))
            else:
                db().execute("INSERT INTO transactions(kind,amount_cents,category,note,occurred_on,user_id) VALUES(?,?,?,?,?,?)",(*values,session["user_id"]))
        db().commit()
        return {"message":"Transaction saved."}, 201 if request.method == "POST" else 200

    return app
