from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import StreamingResponse
import os, io, csv, base64
from supabase import create_client

app = FastAPI()

HOME_CURRENCY = os.environ.get("HOME_CURRENCY", "EUR")
EXCHANGE_RATE = float(os.environ.get("EXCHANGE_RATE", "1"))

CATEGORY_LIST = [
    "Airfare",
    "Hotel",
    "Taxi",
    "Meals - Lunch",
    "Misc - See Comments"
]

def _client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_KEY not set")
    return create_client(url, key)

@app.get("/")
def root():
    return {"message": "Expense app backend running"}

@app.get("/status")
def status():
    return {"status": "ok"}

@app.get("/api/categories")
def categories():
    return CATEGORY_LIST

@app.get("/api/reports")
def list_reports():
    client = _client()
    return client.table("reports").select("*").order("id", desc=True).execute().data

@app.post("/api/reports")
def create_report(name: str = Form(...)):
    client = _client()
    res = client.table("reports").insert({"name": name, "status": "draft"}).execute()
    return res.data[0]

@app.get("/api/expenses/draft")
def draft_expenses():
    client = _client()
    return client.table("expenses").select("*").filter("report_id", "is", None).order("id", desc=True).execute().data

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
    if total_home == 0:
        total_home = amount if trans_currency == HOME_CURRENCY else round(amount * EXCHANGE_RATE, 2)
    res = client.table("expenses").insert(
        {
            "date": date,
            "category": category,
            "amount": amount,
            "trans_currency": trans_currency,
            "total_home": total_home,
            "detail": detail,
            "vendor": vendor,
            "receipt_storage_key": receipt_base64,
        }
    ).execute()
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
    receipt_base64 = base64.b64encode(data).decode()
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
def attach(report_id: int, expense_ids: list[int]):
    client = _client()
    client.table("expenses").update({"report_id": report_id}).filter("id", "in", expense_ids).execute()
    return {"attached": len(expense_ids)}

@app.post("/api/reports/{report_id}/export")
def export(report_id: int):
    client = _client()
    expenses = (
        client.table("expenses")
        .select("*")
        .filter("report_id", "eq", report_id)
        .order("id")
        .execute()
        .data
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Date", "Category", "Amount", "Trans Currency", "Total (Home Currency)", "Comments"])
    for e in expenses:
        writer.writerow(
            [
                e.get("date"),
                e.get("category"),
                e.get("amount"),
                e.get("trans_currency"),
                e.get("total_home"),
                e.get("detail"),
            ]
        )
    csv_bytes = buf.getvalue().encode("utf-8")
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=expense_report_{report_id}.csv"},
    )
