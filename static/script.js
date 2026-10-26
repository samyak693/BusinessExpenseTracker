
const $ = (id) => document.getElementById(id);

const money = (value) =>
    new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR"
    }).format(value);

let expenses = [];
let editingId = null;
let categoryChart = null;

const today = new Date();
const localToday = [
    today.getFullYear(),
    String(today.getMonth() + 1).padStart(2, "0"),
    String(today.getDate()).padStart(2, "0")
].join("-");

const currentMonth = localToday.slice(0, 7);

$("monthFilter").value = currentMonth;
$("expenseDate").value = localToday;

async function api(url, options = {}) {
    const response = await fetch(url, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {})
        }
    });

    const result = await response.json();

    if (!response.ok) {
        throw new Error(result.error || "Something went wrong.");
    }

    return result;
}

async function loadExpenses() {
    const month = $("monthFilter").value || currentMonth;

    try {
        const data = await api(
            `/api/expenses?month=${encodeURIComponent(month)}`
        );

        expenses = data.expenses;

        $("total").textContent = money(data.total);
        $("budgetValue").textContent = money(data.budget);
        $("remaining").textContent = money(data.remaining);
        $("monthTotal").textContent = money(data.total);
        $("count").textContent = data.count;

        $("remaining").classList.toggle(
            "negative",
            data.remaining < 0
        );

        $("budgetMessage").textContent =
            data.remaining < 0
                ? "Budget exceeded"
                : "Available to spend";

        const percent = data.budget > 0
            ? Math.min(data.total / data.budget * 100, 100)
            : 0;

        $("progress").style.width = `${percent}%`;
        $("progress").style.background =
            data.total > data.budget ? "#d64b5c" : "#4466e8";

        $("spentLabel").textContent = `${money(data.total)} spent`;
        $("percentLabel").textContent =
            `${data.budget > 0
                ? (data.total / data.budget * 100).toFixed(1)
                : 0}% used`;

        renderExpenses();
        renderChart(data.category_totals);
    } catch (error) {
        $("expenseRows").innerHTML =
            `<tr><td colspan="5">Unable to load expenses.</td></tr>`;
        alert(error.message);
    }
}

function renderExpenses() {
    const query = $("search").value.trim().toLowerCase();

    const filtered = expenses.filter((expense) =>
        `${expense.title} ${expense.category} ${expense.description || ""}`
            .toLowerCase()
            .includes(query)
    );

    const rows = $("expenseRows");

    rows.replaceChildren();

    if (!filtered.length) {
        const row = rows.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 5;
        cell.textContent = "No expenses found for this month.";
        return;
    }

    filtered.forEach((expense) => {
        const row = rows.insertRow();

        const titleCell = row.insertCell();
        const title = document.createElement("strong");
        title.textContent = expense.title;
        titleCell.appendChild(title);

        row.insertCell().textContent = expense.category;
        row.insertCell().textContent = expense.expense_date;
        row.insertCell().textContent = money(expense.amount);

        const actions = row.insertCell();

        const edit = document.createElement("button");
        edit.textContent = "Edit";
        edit.addEventListener("click", () => openEdit(expense));

        const remove = document.createElement("button");
        remove.textContent = "Delete";
        remove.className = "delete";
        remove.addEventListener("click", () => deleteExpense(expense.id));

        actions.append(edit, remove);
    });
}

function renderChart(categoryTotals) {
    if (typeof Chart === "undefined") {
        return;
    }

    const labels = Object.keys(categoryTotals);
    const values = Object.values(categoryTotals);

    if (categoryChart) {
        categoryChart.destroy();
    }

    categoryChart = new Chart($("categoryChart"), {
        type: "doughnut",
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: [
                    "#4466e8", "#22a78a", "#f2ad4b",
                    "#d96884", "#9272db", "#46a7cc", "#9ca6b8"
                ],
                borderWidth: 2,
                borderColor: "#ffffff"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "bottom"
                }
            }
        }
    });
}

function openAdd() {
    editingId = null;
    $("expenseForm").reset();
    $("formTitle").textContent = "Add Expense";
    $("expenseDate").value = localToday;
    $("formError").textContent = "";
    $("expenseModal").classList.remove("hidden");
}

function openEdit(expense) {
    editingId = expense.id;

    $("formTitle").textContent = "Edit Expense";
    $("title").value = expense.title;
    $("category").value = expense.category;
    $("amount").value = expense.amount;
    $("expenseDate").value = expense.expense_date;
    $("description").value = expense.description || "";
    $("formError").textContent = "";

    $("expenseModal").classList.remove("hidden");
}

function closeExpenseForm() {
    $("expenseModal").classList.add("hidden");
}

async function deleteExpense(id) {
    if (!confirm("Are you sure you want to delete this expense?")) {
        return;
    }

    try {
        await api(`/api/expenses/${id}`, { method: "DELETE" });
        await loadExpenses();
    } catch (error) {
        alert(error.message);
    }
}

$("openForm").addEventListener("click", openAdd);
$("closeForm").addEventListener("click", closeExpenseForm);

$("expenseModal").addEventListener("click", (event) => {
    if (event.target === $("expenseModal")) {
        closeExpenseForm();
    }
});

$("expenseForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    const payload = {
        title: $("title").value.trim(),
        category: $("category").value,
        amount: Number($("amount").value),
        expense_date: $("expenseDate").value,
        description: $("description").value.trim()
    };

    try {
        const url = editingId
            ? `/api/expenses/${editingId}`
            : "/api/expenses";

        await api(url, {
            method: editingId ? "PUT" : "POST",
            body: JSON.stringify(payload)
        });

        closeExpenseForm();
        await loadExpenses();
    } catch (error) {
        $("formError").textContent = error.message;
    }
});

$("monthFilter").addEventListener("change", loadExpenses);
$("search").addEventListener("input", renderExpenses);

$("editBudget").addEventListener("click", async () => {
    try {
        const data = await api(
            `/api/expenses?month=${encodeURIComponent(
                $("monthFilter").value || currentMonth
            )}`
        );

        $("budgetInput").value = data.budget;
        $("budgetError").textContent = "";
        $("budgetModal").classList.remove("hidden");
    } catch (error) {
        alert(error.message);
    }
});

$("closeBudget").addEventListener("click", () => {
    $("budgetModal").classList.add("hidden");
});

$("budgetModal").addEventListener("click", (event) => {
    if (event.target === $("budgetModal")) {
        $("budgetModal").classList.add("hidden");
    }
});

$("budgetForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    try {
        await api("/api/budget", {
            method: "PUT",
            body: JSON.stringify({
                budget: Number($("budgetInput").value)
            })
        });

        $("budgetModal").classList.add("hidden");
        await loadExpenses();
    } catch (error) {
        $("budgetError").textContent = error.message;
    }
});

loadExpenses();

