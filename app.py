
from flask import Flask, render_template, request, redirect, jsonify
import sqlite3
from pathlib import Path
from datetime import date

app = Flask(__name__)

# Keep the database in a persistent application-data folder.
DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "expenses.db"

CATEGORIES = [
    "Salaries", "Rent", "Travel", "Marketing",
    "Equipment", "Utilities", "Other"
]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                expense_date TEXT NOT NULL,
                description TEXT DEFAULT ''
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY CHECK(id = 1),
                monthly_budget REAL NOT NULL DEFAULT 100000
            )
        """)

        conn.execute("""
            INSERT OR IGNORE INTO settings (id, monthly_budget)
            VALUES (1, 100000)
        """)


@app.route("/")
def index():
    return render_template("index.html", categories=CATEGORIES)


@app.get("/api/expenses")
def get_expenses():
    month = request.args.get("month", date.today().strftime("%Y-%m"))

    with get_db() as conn:
        expenses = conn.execute("""
            SELECT * FROM expenses
            WHERE substr(expense_date, 1, 7) = ?
            ORDER BY expense_date DESC, id DESC
        """, (month,)).fetchall()

        budget = conn.execute("""
            SELECT monthly_budget FROM settings WHERE id = 1
        """).fetchone()["monthly_budget"]

    records = [dict(row) for row in expenses]
    total = sum(row["amount"] for row in records)

    category_totals = {}
    for row in records:
        category_totals[row["category"]] = (
            category_totals.get(row["category"], 0) + row["amount"]
        )

    return jsonify({
        "expenses": records,
        "total": round(total, 2),
        "budget": budget,
        "remaining": round(budget - total, 2),
        "count": len(records),
        "category_totals": category_totals
    })


@app.post("/api/expenses")
def add_expense():
    data = request.get_json(silent=True) or {}

    title = str(data.get("title", "")).strip()
    category = str(data.get("category", "")).strip()
    expense_date = str(data.get("expense_date", "")).strip()
    description = str(data.get("description", "")).strip()

    try:
        amount = float(data.get("amount", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Enter a valid amount."}), 400

    if not title or len(title) > 100:
        return jsonify({"error": "Title is required (maximum 100 characters)."}), 400

    if category not in CATEGORIES:
        return jsonify({"error": "Select a valid category."}), 400

    if not amount > 0 or amount > 1000000000:
        return jsonify({"error": "Amount must be greater than zero."}), 400

    try:
        parsed_date = date.fromisoformat(expense_date)
    except ValueError:
        return jsonify({"error": "Enter a valid date."}), 400

    if parsed_date.isoformat() != expense_date:
        return jsonify({"error": "Enter a valid date."}), 400

    if len(description) > 500:
        return jsonify({"error": "Description is too long."}), 400

    with get_db() as conn:
        conn.execute("""
            INSERT INTO expenses
                (title, category, amount, expense_date, description)
            VALUES (?, ?, ?, ?, ?)
        """, (title, category, amount, expense_date, description))

    return jsonify({"message": "Expense added successfully."}), 201


@app.put("/api/expenses/<int:expense_id>")
def update_expense(expense_id):
    data = request.get_json(silent=True) or {}

    title = str(data.get("title", "")).strip()
    category = str(data.get("category", "")).strip()
    expense_date = str(data.get("expense_date", "")).strip()
    description = str(data.get("description", "")).strip()

    try:
        amount = float(data.get("amount", 0))
        parsed_date = date.fromisoformat(expense_date)
    except (TypeError, ValueError):
        return jsonify({"error": "Enter a valid amount and date."}), 400

    if (
        not title or len(title) > 100
        or category not in CATEGORIES
        or not 0 < amount <= 1000000000
        or parsed_date.isoformat() != expense_date
        or len(description) > 500
    ):
        return jsonify({"error": "Check the expense details."}), 400

    with get_db() as conn:
        result = conn.execute("""
            UPDATE expenses
            SET title = ?, category = ?, amount = ?,
                expense_date = ?, description = ?
            WHERE id = ?
        """, (
            title, category, amount, expense_date,
            description, expense_id
        ))

    if result.rowcount == 0:
        return jsonify({"error": "Expense not found."}), 404

    return jsonify({"message": "Expense updated successfully."})


@app.delete("/api/expenses/<int:expense_id>")
def delete_expense(expense_id):
    with get_db() as conn:
        result = conn.execute(
            "DELETE FROM expenses WHERE id = ?",
            (expense_id,)
        )

    if result.rowcount == 0:
        return jsonify({"error": "Expense not found."}), 404

    return jsonify({"message": "Expense deleted successfully."})


@app.put("/api/budget")
def update_budget():
    data = request.get_json(silent=True) or {}

    try:
        budget = float(data.get("budget", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Enter a valid budget."}), 400

    if not 0 <= budget <= 1000000000:
        return jsonify({"error": "Budget must be between 0 and 1,000,000,000."}), 400

    with get_db() as conn:
        conn.execute("""
            UPDATE settings SET monthly_budget = ? WHERE id = 1
        """, (budget,))

    return jsonify({"message": "Budget updated successfully."})


@app.get("/health")
def health():
    with get_db() as conn:
        conn.execute("SELECT 1").fetchone()
    return jsonify({"status": "healthy"})

@app.get("/api/insights")
def financial_insights():
    month = request.args.get("month", date.today().strftime("%Y-%m"))

    try:
        parsed_month = date.fromisoformat(month + "-01")
    except ValueError:
        return jsonify({"error": "Month must use YYYY-MM format."}), 400

    if parsed_month.strftime("%Y-%m") != month:
        return jsonify({"error": "Month must use YYYY-MM format."}), 400

    with get_db() as conn:
        rows = conn.execute("""
            SELECT category, amount
            FROM expenses
            WHERE substr(expense_date, 1, 7) = ?
        """, (month,)).fetchall()

        budget = conn.execute("""
            SELECT monthly_budget FROM settings WHERE id = 1
        """).fetchone()["monthly_budget"]

    total = sum(row["amount"] for row in rows)
    remaining = budget - total
    categories = {}

    for row in rows:
        categories[row["category"]] = (
            categories.get(row["category"], 0) + row["amount"]
        )

    highest = max(categories, key=categories.get) if categories else None
    percent = total / budget * 100 if budget > 0 else 0

    insights = []

    if budget == 0:
        insights.append("Your monthly budget is zero. Set a budget to track your limit.")
    elif total > budget:
        insights.append(f"Budget exceeded by ₹{total - budget:,.2f}. Review optional expenses.")
    elif percent >= 80:
        insights.append(f"You have used {percent:.1f}% of your monthly budget. Spend carefully.")
    else:
        insights.append(f"You have used {percent:.1f}% of your monthly budget.")

    if highest:
        insights.append(
            f"{highest} is your highest-spending category at ₹{categories[highest]:,.2f}."
        )
    else:
        insights.append("No expenses have been recorded for this month.")

    return jsonify({
        "month": month,
        "total": round(total, 2),
        "budget": budget,
        "remaining": round(remaining, 2),
        "budget_used_percent": round(percent, 1),
        "highest_category": highest,
        "insights": insights
    })


init_db()


@app.post("/api/assistant")
def financial_assistant():
    data = request.get_json(silent=True) or {}
    question = str(data.get("question", "")).strip().lower()

    if not question:
        return jsonify({"answer": "Please ask me a financial question."}), 400

    month = date.today().strftime("%Y-%m")

    with get_db() as conn:
        expenses = conn.execute("""
            SELECT title, category, amount, expense_date
            FROM expenses
            WHERE substr(expense_date, 1, 7) = ?
        """, (month,)).fetchall()

        budget = conn.execute("""
            SELECT monthly_budget FROM settings WHERE id = 1
        """).fetchone()["monthly_budget"]

    total = sum(row["amount"] for row in expenses)
    remaining = budget - total

    categories = {}
    for row in expenses:
        categories[row["category"]] = (
            categories.get(row["category"], 0) + row["amount"]
        )

    highest = max(categories, key=categories.get) if categories else None
    money = lambda value: f"₹{value:,.2f}"

    if any(word in question for word in ["highest", "most", "category", "where"]):
        if highest:
            answer = (
                f"Your highest spending category this month is {highest}, "
                f"with {money(categories[highest])} spent."
            )
        else:
            answer = "You have no recorded expenses this month yet."

    elif any(word in question for word in ["budget", "remaining", "left", "limit"]):
        answer = (
            f"Your monthly budget is {money(budget)}. "
            f"You have spent {money(total)}, with "
            f"{money(remaining)} remaining."
        )
        if remaining < 0:
            answer += f" You are over budget by {money(abs(remaining))}."

    elif any(word in question for word in ["reduce", "save", "saving", "cut"]):
        if highest:
            answer = (
                f"Your {highest} category has the highest spending at "
                f"{money(categories[highest])}. Review these expenses for "
                "possible savings and compare them with your business needs."
            )
        else:
            answer = "Record some expenses first so I can suggest savings."

    elif any(word in question for word in ["summary", "total", "spent", "expense"]):
        answer = (
            f"This month's total spending is {money(total)} across "
            f"{len(expenses)} transactions. Your budget is {money(budget)} "
            f"and the remaining amount is {money(remaining)}."
        )
        if highest:
            answer += (
                f" Your highest category is {highest} "
                f"({money(categories[highest])})."
            )

    else:
        answer = (
            "I can help with your monthly spending, budget remaining, "
            "highest-spending category, and saving suggestions. "
            "Try asking: 'Give me a summary' or 'Where am I spending the most?'"
        )

    return jsonify({"answer": answer})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)

