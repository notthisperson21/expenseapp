from fastapi import FastAPI, File, UploadFile, Form, Body
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse
from supabase import create_client
import os
import io
import csv
import base64
import textwrap

app = FastAPI()

HOME_CURRENCY = os.environ.get("HOME_CURRENCY", "EUR")
EXCHANGE_RATE = float(os.environ.get("EXCHANGE_RATE", "1"))

CATEGORY_LIST = [
    "Airfare",
    "FX/ATM/Bank Fees",
    "Cell Phone",
    "Gas for Rental Car",
    "Hotel",
    "Internet",
    "Misc - Laundry",
    "Meals - Breakfast",
    "Meals - Lunch",
    "Meals - Dinner",
    "Meals - Groceries",
    "Meals - Snacks",
    "Medical - Shots for Travel",
    "Misc - See Comments",
    "Misc - Tips",
    "Parking - Airport",
    "Rental Car",
    "Taxi/Train/Subway",
    "Visa/Entrance/Exit Fee's",
]


def _client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_KEY not set")
    return create_client(url, key)


def _compute_total_home(amount: float, trans_currency: str) -> float:
    if not amount:
        return 0.0
    if (trans_currency or HOME_CURRENCY).upper() == HOME_CURRENCY.upper():
        return round(float(amount), 2)
    return round(float(amount) * EXCHANGE_RATE, 2)


@app.get("/", response_class=HTMLResponse)
def root():
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Expense App</title>
      <style>
        :root {
          --bg: #0b1020;
          --bg-2: #121932;
          --card: rgba(255,255,255,0.08);
          --card-2: rgba(255,255,255,0.06);
          --line: rgba(255,255,255,0.12);
          --text: #eef2ff;
          --muted: #aab3d1;
          --accent: #7c9cff;
          --accent-2: #5ce1c6;
          --danger: #ff6b81;
          --shadow: 0 20px 50px rgba(0,0,0,.35);
          --radius: 20px;
        }

        * { box-sizing: border-box; }
        html, body {
          margin: 0;
          font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          background:
            radial-gradient(circle at top left, rgba(124,156,255,.18), transparent 28%),
            radial-gradient(circle at top right, rgba(92,225,198,.12), transparent 22%),
            linear-gradient(180deg, #08101f 0%, #0b1020 100%);
          color: var(--text);
          min-height: 100%;
        }

        .shell {
          max-width: 1280px;
          margin: 0 auto;
          padding: 24px;
        }

        .hero {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 20px;
          padding: 26px;
          border: 1px solid var(--line);
          border-radius: 28px;
          background: linear-gradient(180deg, rgba(255,255,255,.09), rgba(255,255,255,.05));
          box-shadow: var(--shadow);
          backdrop-filter: blur(18px);
          margin-bottom: 22px;
        }

        .hero h1 {
          margin: 0 0 6px 0;
          font-size: 32px;
          line-height: 1.05;
          letter-spacing: -.03em;
        }

        .hero p {
          margin: 0;
          color: var(--muted);
          font-size: 15px;
        }

        .pillbar {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
          margin-top: 16px;
        }

        .pill {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 9px 12px;
          border: 1px solid var(--line);
          border-radius: 999px;
          background: rgba(255,255,255,.05);
          color: var(--muted);
          font-size: 13px;
        }

        .layout {
          display: grid;
          grid-template-columns: 380px 1fr;
          gap: 20px;
        }

        @media (max-width: 980px) {
          .layout {
            grid-template-columns: 1fr;
          }
        }

        .stack {
          display: grid;
          gap: 18px;
        }

        .card {
          border: 1px solid var(--line);
          background: linear-gradient(180deg, rgba(255,255,255,.08), rgba(255,255,255,.045));
          border-radius: var(--radius);
          padding: 18px;
          box-shadow: var(--shadow);
          backdrop-filter: blur(16px);
        }

        .card h2 {
          margin: 0 0 6px 0;
          font-size: 18px;
          letter-spacing: -.02em;
        }

        .sub {
          margin: 0 0 14px 0;
          color: var(--muted);
          font-size: 13px;
        }

        .grid-2 {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
        }

        @media (max-width: 560px) {
          .grid-2 {
            grid-template-columns: 1fr;
          }
        }

        label {
          display: block;
          font-size: 12px;
          color: var(--muted);
          margin-bottom: 6px;
        }

        input, select, textarea {
          width: 100%;
          border: 1px solid rgba(255,255,255,.12);
          background: rgba(5,10,25,.45);
          color: var(--text);
          border-radius: 14px;
          padding: 12px 14px;
          outline: none;
          font-size: 14px;
          transition: .18s ease;
        }

        input:focus, select:focus, textarea:focus {
          border-color: rgba(124,156,255,.7);
          box-shadow: 0 0 0 4px rgba(124,156,255,.12);
        }

        textarea {
          min-height: 92px;
          resize: vertical;
        }

        .actions {
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
          margin-top: 14px;
        }

        button {
          border: 0;
          border-radius: 14px;
          padding: 12px 16px;
          font-size: 14px;
          font-weight: 700;
          cursor: pointer;
          transition: transform .12s ease, opacity .12s ease, background .12s ease;
        }

        button:hover { transform: translateY(-1px); }
        button:active { transform: translateY(0); }

        .btn-primary {
          background: linear-gradient(135deg, var(--accent), #99aeff);
          color: #09111f;
        }

        .btn-secondary {
          background: rgba(255,255,255,.08);
          color: var(--text);
          border: 1px solid var(--line);
        }

        .btn-danger {
          background: rgba(255,107,129,.15);
          color: #ffd6dc;
          border: 1px solid rgba(255,107,129,.28);
        }

        .kpi-row {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 12px;
          margin-bottom: 18px;
        }

        @media (max-width: 980px) {
          .kpi-row { grid-template-columns: repeat(2, 1fr); }
        }

        @media (max-width: 560px) {
          .kpi-row { grid-template-columns: 1fr; }
        }

        .kpi {
          padding: 16px;
          border-radius: 18px;
          border: 1px solid var(--line);
          background: var(--card-2);
        }

        .kpi .label {
          color: var(--muted);
          font-size: 12px;
          margin-bottom: 8px;
        }

        .kpi .value {
          font-size: 28px;
          font-weight: 800;
          letter-spacing: -.03em;
        }

        .toolbar {
          display: flex;
          gap: 10px;
          justify-content: space-between;
          align-items: center;
          flex-wrap: wrap;
          margin-bottom: 16px;
        }

        .search {
          flex: 1;
          min-width: 220px;
        }

        .expense-list, .report-list {
          display: grid;
          gap: 12px;
        }

        .expense-item, .report-item {
          border: 1px solid var(--line);
          background: rgba(255,255,255,.04);
          border-radius: 18px;
          padding: 14px;
        }

        .expense-top, .report-top {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 12px;
        }

        .expense-title, .report-title {
          font-size: 16px;
          font-weight: 700;
          margin: 0 0 4px 0;
        }

        .expense-meta, .report-meta {
          color: var(--muted);
          font-size: 13px;
        }

        .badge {
          display: inline-flex;
          align-items: center;
          white-space: nowrap;
          border-radius: 999px;
          padding: 8px 10px;
          background: rgba(92,225,198,.12);
          color: #b6fff0;
          border: 1px solid rgba(92,225,198,.22);
          font-size: 12px;
          font-weight: 700;
        }

        .expense-bottom {
          display: flex;
          justify-content: space-between;
          gap: 12px;
          margin-top: 12px;
          align-items: center;
          flex-wrap: wrap;
        }

        .expense-actions, .report-actions {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
        }

        .chips {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-top: 10px;
        }

        .chip {
          border-radius: 999px;
          padding: 6px 10px;
          font-size: 12px;
          color: var(--muted);
          background: rgba(255,255,255,.05);
          border: 1px solid var(--line);
        }

        .empty {
          padding: 18px;
          text-align: center;
          border: 1px dashed rgba(255,255,255,.15);
          color: var(--muted);
          border-radius: 18px;
          background: rgba(255,255,255,.03);
        }

        .toast {
          position: fixed;
          right: 18px;
          bottom: 18px;
          min-width: 220px;
          max-width: 360px;
          padding: 14px 16px;
          border-radius: 16px;
          border: 1px solid var(--line);
          background: rgba(11,16,32,.94);
          box-shadow: var(--shadow);
          color: var(--text);
          transform: translateY(20px);
          opacity: 0;
          pointer-events: none;
          transition: .18s ease;
          z-index: 9999;
        }

        .toast.show {
          transform: translateY(0);
          opacity: 1;
        }

        .small {
          font-size: 12px;
          color: var(--muted);
        }

        .linkish {
          color: #bdd0ff;
          text-decoration: none;
        }

        .preview {
          display: none;
          margin-top: 12px;
          border-radius: 16px;
          overflow: hidden;
          border: 1px solid var(--line);
          background: rgba(255,255,255,.03);
        }

        .preview img {
          display: block;
          width: 100%;
          max-height: 260px;
          object-fit: contain;
          background: #0a1225;
        }
      </style>
    </head>
    <body>
      <div class="shell">
        <div class="hero">
          <div>
            <h1>Expense App</h1>
            <p>Save draft expenses on the go, attach receipts, group them into reports, and export when you're ready.</p>
            <div class="pillbar">
              <div class="pill">Supabase-backed</div>
              <div class="pill">Mobile friendly</div>
              <div class="pill">Receipt upload</div>
              <div class="pill">Draft workflow</div>
            </div>
          </div>
        </div>

        <div class="kpi-row">
          <div class="kpi">
            <div class="label">Draft expenses</div>
            <div class="value" id="kpiDrafts">0</div>
          </div>
          <div class="kpi">
            <div class="label">Draft total</div>
            <div class="value" id="kpiTotal">0.00</div>
          </div>
          <div class="kpi">
            <div class="label">Reports</div>
            <div class="value" id="kpiReports">0</div>
          </div>
          <div class="kpi">
            <div class="label">Home currency</div>
            <div class="value" id="kpiCurrency">EUR</div>
          </div>
        </div>

        <div class="layout">
          <div class="stack">
            <div class="card">
              <h2>New report</h2>
              <p class="sub">Create a report first, or save expenses as drafts and attach them later.</p>
              <form id="reportForm">
                <label for="reportName">Report name</label>
                <input id="reportName" name="name" placeholder="April 2026 Germany travel" required />
                <div class="actions">
                  <button class="btn-primary" type="submit">Create report</button>
                </div>
              </form>
            </div>

            <div class="card">
              <h2>Add expense</h2>
              <p class="sub">Quick entry for a receipt or manual expense.</p>
              <form id="expenseForm">
                <div class="grid-2">
                  <div>
                    <label for="date">Date</label>
                    <input id="date" name="date" type="date" />
                  </div>
                  <div>
                    <label for="category">Category</label>
                    <select id="category" name="category"></select>
                  </div>
                </div>

                <div class="grid-2">
                  <div>
                    <label for="amount">Amount</label>
                    <input id="amount" name="amount" type="number" step="0.01" placeholder="0.00" />
                  </div>
                  <div>
                    <label for="currency">Currency</label>
                    <input id="currency" name="trans_currency" value="EUR" />
                  </div>
                </div>

                <label for="vendor">Vendor</label>
                <input id="vendor" name="vendor" placeholder="Uber, Hilton, Lufthansa..." />

                <label for="detail">Comment / detail</label>
                <textarea id="detail" name="detail" placeholder="What was this for?"></textarea>

                <label for="receipt">Receipt image</label>
                <input id="receipt" name="file" type="file" accept="image/*,.jpg,.jpeg,.png,.webp" />
                <div id="preview" class="preview"><img id="previewImg" alt="Receipt preview" /></div>

                <div class="actions">
                  <button class="btn-primary" type="submit">Save draft expense</button>
                  <button class="btn-secondary" id="clearExpense" type="button">Clear</button>
                </div>
              </form>
            </div>
          </div>

          <div class="stack">
            <div class="card">
              <div class="toolbar">
                <div>
                  <h2 style="margin-bottom:4px;">Draft expenses</h2>
                  <div class="sub" style="margin:0;">Select drafts and attach them to a report.</div>
                </div>
                <input class="search" id="searchDrafts" placeholder="Search vendor, category, detail..." />
              </div>
              <div id="draftList" class="expense-list"></div>
            </div>

            <div class="card">
              <div class="toolbar">
                <div>
                  <h2 style="margin-bottom:4px;">Reports</h2>
                  <div class="sub" style="margin:0;">Attach selected drafts or export a report.</div>
                </div>
              </div>
              <div id="reportList" class="report-list"></div>
            </div>
          </div>
        </div>
      </div>

      <div id="toast" class="toast"></div>

      <script>
        const state = {
          categories: [],
          drafts: [],
          reports: [],
          selectedDraftIds: new Set(),
        };

        function money(n) {
          const num = Number(n || 0);
          return num.toFixed(2);
        }

        function toast(message, isError = false) {
          const el = document.getElementById("toast");
          el.textContent = message;
          el.style.borderColor = isError ? "rgba(255,107,129,.35)" : "rgba(124,156,255,.25)";
          el.classList.add("show");
          clearTimeout(window.__toastTimer);
          window.__toastTimer = setTimeout(() => el.classList.remove("show"), 2600);
        }

        function escapeHtml(str) {
          return String(str || "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
        }

        async function api(url, options = {}) {
          const res = await fetch(url, options);
          if (!res.ok) {
            let text = await res.text();
            throw new Error(text || `Request failed: ${res.status}`);
          }
          const ct = res.headers.get("content-type") || "";
          if (ct.includes("application/json")) return res.json();
          return res.text();
        }

        async function loadCategories() {
          state.categories = await api("/api/categories");
          const select = document.getElementById("category");
          select.innerHTML = state.categories
            .map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`)
            .join("");
        }

        async function loadDrafts() {
          state.drafts = await api("/api/expenses/draft");
          renderDrafts();
          renderKpis();
        }

        async function loadReports() {
          state.reports = await api("/api/reports");
          renderReports();
          renderKpis();
        }

        function renderKpis() {
          document.getElementById("kpiDrafts").textContent = state.drafts.length;
          document.getElementById("kpiReports").textContent = state.reports.length;
          document.getElementById("kpiCurrency").textContent = "EUR";
          const total = state.drafts.reduce((sum, d) => sum + Number(d.total_home || 0), 0);
          document.getElementById("kpiTotal").textContent = money(total);
        }

        function toggleDraft(id) {
          if (state.selectedDraftIds.has(id)) state.selectedDraftIds.delete(id);
          else state.selectedDraftIds.add(id);
          renderDrafts();
          renderReports();
        }

        function renderDrafts() {
          const container = document.getElementById("draftList");
          const q = (document.getElementById("searchDrafts").value || "").toLowerCase().trim();

          const filtered = state.drafts.filter(d => {
            if (!q) return true;
            const blob = `${d.vendor || ""} ${d.category || ""} ${d.detail || ""} ${d.date || ""}`.toLowerCase();
            return blob.includes(q);
          });

          if (!filtered.length) {
            container.innerHTML = '<div class="empty">No draft expenses yet.</div>';
            return;
          }

          container.innerHTML = filtered.map(d => {
            const checked = state.selectedDraftIds.has(d.id);
            return `
              <div class="expense-item">
                <div class="expense-top">
                  <div>
                    <div class="expense-title">${escapeHtml(d.vendor || "Untitled expense")}</div>
                    <div class="expense-meta">
                      ${escapeHtml(d.date || "No date")} · ${escapeHtml(d.category || "No category")}
                    </div>
                    <div class="chips">
                      <div class="chip">${escapeHtml(d.trans_currency || "EUR")} ${money(d.amount)}</div>
                      <div class="chip">Home: ${money(d.total_home)}</div>
                      ${d.receipt_storage_key ? '<div class="chip">Receipt attached</div>' : ''}
                    </div>
                  </div>
                  <div class="badge">${checked ? "Selected" : "Draft"}</div>
                </div>
                <div class="expense-bottom">
                  <div class="small">${escapeHtml(d.detail || "")}</div>
                  <div class="expense-actions">
                    <button class="btn-secondary" onclick="toggleDraft(${d.id})">
                      ${checked ? "Unselect" : "Select"}
                    </button>
                  </div>
                </div>
              </div>
            `;
          }).join("");
        }

        function renderReports() {
          const container = document.getElementById("reportList");
          if (!state.reports.length) {
            container.innerHTML = '<div class="empty">No reports yet.</div>';
            return;
          }

          const selectedCount = state.selectedDraftIds.size;

          container.innerHTML = state.reports.map(r => `
            <div class="report-item">
              <div class="report-top">
                <div>
                  <div class="report-title">${escapeHtml(r.name)}</div>
                  <div class="report-meta">Status: ${escapeHtml(r.status || "draft")} · ID: ${r.id}</div>
                </div>
                <div class="badge">Report</div>
              </div>
              <div class="report-actions" style="margin-top:12px;">
                <button class="btn-primary" onclick="attachToReport(${r.id})" ${selectedCount ? "" : "disabled"}>
                  Attach ${selectedCount ? selectedCount : ""} selected
                </button>
                <button class="btn-secondary" onclick="exportReport(${r.id})">Export CSV</button>
              </div>
            </div>
          `).join("");
        }

        async function attachToReport(reportId) {
          const ids = Array.from(state.selectedDraftIds);
          if (!ids.length) {
            toast("Select at least one draft first.", true);
            return;
          }

          try {
            await api(`/api/reports/${reportId}/attach`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(ids),
            });
            state.selectedDraftIds.clear();
            toast("Drafts attached to report.");
            await loadDrafts();
            await loadReports();
          } catch (err) {
            toast("Could not attach drafts.", true);
          }
        }

        function exportReport(reportId) {
          window.open(`/api/reports/${reportId}/export`, "_blank");
        }

        async function createReport(e) {
          e.preventDefault();
          const fd = new FormData(e.target);
          try {
            await api("/api/reports", { method: "POST", body: fd });
            e.target.reset();
            toast("Report created.");
            await loadReports();
          } catch (err) {
            toast("Could not create report.", true);
          }
        }

        async function createExpense(e) {
          e.preventDefault();
          const form = e.target;
          const fileInput = document.getElementById("receipt");

          try {
            let res;
            if (fileInput.files && fileInput.files[0]) {
              const fd = new FormData(form);
              res = await api("/api/expenses/upload", {
                method: "POST",
                body: fd,
              });
            } else {
              const fd = new FormData(form);
              res = await api("/api/expenses", {
                method: "POST",
                body: fd,
              });
            }

            form.reset();
            document.getElementById("currency").value = "EUR";
            document.getElementById("preview").style.display = "none";
            state.selectedDraftIds.clear();
            toast("Draft expense saved.");
            await loadDrafts();
            await loadReports();
          } catch (err) {
            toast("Could not save expense.", true);
          }
        }

        function setupReceiptPreview() {
          const input = document.getElementById("receipt");
          const preview = document.getElementById("preview");
          const img = document.getElementById("previewImg");

          input.addEventListener("change", () => {
            const file = input.files && input.files[0];
            if (!file) {
              preview.style.display = "none";
              return;
            }
            const url = URL.createObjectURL(file);
            img.src = url;
            preview.style.display = "block";
          });
        }

        function clearExpenseForm() {
          document.getElementById("expenseForm").reset();
          document.getElementById("currency").value = "EUR";
          document.getElementById("preview").style.display = "none";
        }

        async function init() {
          document.getElementById("reportForm").addEventListener("submit", createReport);
          document.getElementById("expenseForm").addEventListener("submit", createExpense);
          document.getElementById("searchDrafts").addEventListener("input", renderDrafts);
          document.getElementById("clearExpense").addEventListener("click", clearExpenseForm);
          setupReceiptPreview();

          try {
            await loadCategories();
            await loadDrafts();
            await loadReports();
          } catch (err) {
            toast("App loaded, but backend setup is incomplete.", true);
          }
        }

        init();
      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=textwrap.dedent(html))


@app.get("/status")
def status():
    return {"status": "ok"}


@app.get("/api/categories")
def categories():
    return CATEGORY_LIST


@app.get("/api/reports")
def list_reports():
    client = _client()
    res = client.table("reports").select("*").order("id", desc=True).execute()
    return res.data or []


@app.post("/api/reports")
def create_report(name: str = Form(...)):
    client = _client()
    res = client.table("reports").insert({"name": name, "status": "draft"}).execute()
    if not res.data:
        return JSONResponse({"error": "Could not create report"}, status_code=500)
    return res.data[0]


@app.get("/api/expenses/draft")
def draft_expenses():
    client = _client()
    res = (
        client.table("expenses")
        .select("*")
        .filter("report_id", "is", None)
        .order("id", desc=True)
        .execute()
    )
    return res.data or []


@app.post("/api/expenses")
def create_expense(
    date: str = Form(""),
    category: str = Form("Misc - See Comments"),
    amount: float = Form(0.0),
    trans_currency: str = Form("EUR"),
    total_home: float = Form(0.0),
    detail: str = Form(""),
    vendor: str = Form(""),
    receipt_base64: str = Form("")
):
    client = _client()

    if not total_home:
        total_home = _compute_total_home(amount, trans_currency)

    payload = {
        "date": date,
        "category": category,
        "amount": amount,
        "trans_currency": trans_currency,
        "total_home": total_home,
        "detail": detail,
        "vendor": vendor,
        "receipt_storage_key": receipt_base64,
    }

    res = client.table("expenses").insert(payload).execute()
    if not res.data:
        return JSONResponse({"error": "Could not create expense"}, status_code=500)
    return res.data[0]


@app.post("/api/expenses/upload")
async def upload_expense(
    file: UploadFile = File(...),
    date: str = Form(""),
    category: str = Form("Misc - See Comments"),
    amount: float = Form(0.0),
    trans_currency: str = Form("EUR"),
    detail: str = Form(""),
    vendor: str = Form(""),
):
    data = await file.read()
    receipt_base64 = base64.b64encode(data).decode("utf-8")
    return create_expense(
        date=date,
        category=category,
        amount=amount,
        trans_currency=trans_currency,
        total_home=0.0,
        detail=detail,
        vendor=vendor,
        receipt_base64=receipt_base64,
    )


@app.post("/api/reports/{report_id}/attach")
def attach(report_id: int, expense_ids: list[int] = Body(...)):
    client = _client()

    if not expense_ids:
        return {"attached": 0}

    # Supabase Python client expects a PostgREST-style in filter string.
    id_list = ",".join(str(i) for i in expense_ids)

    client.table("expenses").update({"report_id": report_id}).filter("id", "in", f"({id_list})").execute()
    return {"attached": len(expense_ids), "report_id": report_id}


@app.get("/api/reports/{report_id}/export")
def export(report_id: int):
    client = _client()

    expenses = (
        client.table("expenses")
        .select("*")
        .filter("report_id", "eq", report_id)
        .order("id")
        .execute()
        .data
    ) or []

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Date",
        "Category",
        "Amount",
        "Trans Currency",
        "Total (Home Currency)",
        "Comments",
        "Vendor",
    ])

    for e in expenses:
        writer.writerow([
            e.get("date"),
            e.get("category"),
            e.get("amount"),
            e.get("trans_currency"),
            e.get("total_home"),
            e.get("detail"),
            e.get("vendor"),
        ])

    csv_bytes = buf.getvalue().encode("utf-8")

    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="expense_report_{report_id}.csv"'
        },
    )
