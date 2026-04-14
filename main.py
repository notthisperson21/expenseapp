import pytesseract
from PIL import Image
import re
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
    "Airfare","FX/ATM/Bank Fees","Cell Phone","Gas for Rental Car","Hotel","Internet",
    "Misc - Laundry","Meals - Breakfast","Meals - Lunch","Meals - Dinner","Meals - Groceries",
    "Meals - Snacks","Medical - Shots for Travel","Misc - See Comments","Misc - Tips",
    "Parking - Airport","Rental Car","Taxi/Train/Subway","Visa/Entrance/Exit Fee's"
]

# ---------- UTIL ----------
def _client():
    return create_client(
        os.environ.get("SUPABASE_URL"),
        os.environ.get("SUPABASE_SERVICE_KEY")
    )

def _compute_total_home(amount, currency):
    if currency.upper() == HOME_CURRENCY:
        return round(float(amount), 2)
    return round(float(amount) * EXCHANGE_RATE, 2)

# ---------- OCR ----------
def extract_receipt_data(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(img)

        # Better parsing
        amount = 0.0
        amounts = re.findall(r"\d+[.,]\d{2}", text)
        if amounts:
            amount = float(amounts[-1].replace(",", "."))

        date = ""
        dates = re.findall(r"\d{2}[/-]\d{2}[/-]\d{2,4}", text)
        if dates:
            date = dates[0]

        vendor = ""
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if lines:
            vendor = lines[0][:50]

        return {
            "amount": amount,
            "date": date,
            "vendor": vendor
        }

    except Exception:
        return {}

# ---------- ROUTES ----------
@app.get("/")
def root():
    # KEEP YOUR EXISTING HTML (unchanged)
    return HTMLResponse("App running")

@app.get("/status")
def status():
    return {"status": "ok"}

@app.get("/api/categories")
def categories():
    return CATEGORY_LIST

# ---------- REPORTS ----------
@app.get("/api/reports")
def list_reports():
    return _client().table("reports").select("*").order("id", desc=True).execute().data or []

@app.post("/api/reports")
def create_report(name: str = Form(...)):
    res = _client().table("reports").insert({
        "name": name,
        "status": "draft"
    }).execute()

    if not res.data:
        return JSONResponse({"error": "report failed"}, status_code=500)

    return res.data[0]

# ---------- EXPENSES ----------
@app.get("/api/expenses/draft")
def draft_expenses():
    return _client().table("expenses")\
        .select("*")\
        .filter("report_id", "is", None)\
        .order("id", desc=True)\
        .execute().data or []

@app.post("/api/expenses")
def create_expense(
    date: str = Form(""),
    category: str = Form("Misc - See Comments"),
    amount: float = Form(0.0),
    trans_currency: str = Form("EUR"),
    detail: str = Form(""),
    vendor: str = Form(""),
    receipt_base64: str = Form("")
):
    total_home = _compute_total_home(amount, trans_currency)

    res = _client().table("expenses").insert({
        "date": date,
        "category": category,
        "amount": amount,
        "trans_currency": trans_currency,
        "total_home": total_home,
        "detail": detail,
        "vendor": vendor,
        "receipt_storage_key": receipt_base64
    }).execute()

    if not res.data:
        return JSONResponse({"error": "expense failed"}, status_code=500)

    return res.data[0]

# ---------- UPLOAD + OCR ----------
@app.post("/api/expenses/upload")
async def upload_expense(
    file: UploadFile = File(...),
    category: str = Form("Misc - See Comments"),
    trans_currency: str = Form("EUR"),
    detail: str = Form(""),
):
    data = await file.read()

    # OCR extraction
    ocr = extract_receipt_data(data)

    amount = ocr.get("amount", 0.0)
    date = ocr.get("date", "")
    vendor = ocr.get("vendor", "")

    receipt_base64 = base64.b64encode(data).decode()

    return create_expense(
        date=date,
        category=category,
        amount=amount,
        trans_currency=trans_currency,
        detail=detail,
        vendor=vendor,
        receipt_base64=receipt_base64
    )

# ---------- ATTACH ----------
@app.post("/api/reports/{report_id}/attach")
def attach(report_id: int, expense_ids: list[int] = Body(...)):
    if not expense_ids:
        return {"attached": 0}

    id_list = ",".join(map(str, expense_ids))

    _client().table("expenses")\
        .update({"report_id": report_id})\
        .filter("id", "in", f"({id_list})")\
        .execute()

    return {"attached": len(expense_ids)}

# ---------- EXPORT ----------
@app.get("/api/reports/{report_id}/export")
def export(report_id: int):
    expenses = _client().table("expenses")\
        .select("*")\
        .filter("report_id", "eq", report_id)\
        .execute().data or []

    buf = io.StringIO()
    writer = csv.writer(buf)

    writer.writerow([
        "Date","Category","Amount","Currency","Total","Detail","Vendor"
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

    return StreamingResponse(
        io.BytesIO(buf.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=report_{report_id}.csv"}
    )
