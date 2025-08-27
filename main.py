from __future__ import annotations
from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional, Dict, Any, List
import base64
import itertools
import mimetypes
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = FastAPI(title="Restaurant DB - Dashboard & Manage")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

MENU_DB: List[Dict[str, Any]] = []
SERVICE_DB: List[Dict[str, Any]] = []
menu_id_seq = itertools.count(1)
service_id_seq = itertools.count(1)

def encode_upload_to_data_url(file: UploadFile) -> Optional[str]:
    if file is None:
        return None
    if not getattr(file, "filename", None):
        return None
    content = file.file.read()
    if not content:
        return None
    mime = file.content_type or mimetypes.guess_type(file.filename)[0] or "application/octet-stream"
    b64 = base64.b64encode(content).decode("ascii")
    return f"data:{mime};base64,{b64}"

def coerce_price(raw: str) -> int:
    txt = (raw or "").strip().replace(",", "")
    if not txt:
        raise ValueError("Price required")
    value = float(txt)
    if value < 0:
        raise ValueError("Price cannot be negative")
    cents = int(round(value * 100))
    return cents

def price_fmt(cents: int) -> str:
    return f"₱{cents/100:,.2f}"

def seed_data() -> None:
    if MENU_DB or SERVICE_DB:
        return
    def px(color_hex: str) -> str:
        COLORS = {
            "#FDE68A": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAuMBgKkq2AkAAAAASUVORK5CYII=",
            "#BFDBFE": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8zw8AAl8B1q1qj1AAAAAASUVORK5CYII=",
            "#C7F9CC": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8zQ8AAiEB0oXvCwAAAABJRU5ErkJggg==",
            "#FBCFE8": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8Pw8AAmIBq1o7SgAAAABJRU5ErkJggg==",
        }
        b64 = COLORS.get(color_hex, list(COLORS.values())[0])
        return f"data:image/png;base64,{b64}"

    sample_menu = [
        {
            "id": next(menu_id_seq),
            "name": "Classic Burger",
            "price_cents": coerce_price("199"),
            "image": px("#FDE68A"),
            "description": "Grilled beef patty, cheddar, lettuce, tomato, house sauce.",
        },
        {
            "id": next(menu_id_seq),
            "name": "Chicken Alfredo",
            "price_cents": coerce_price("249.50"),
            "image": px("#BFDBFE"),
            "description": "Creamy pasta with roasted chicken and parmesan.",
        },
        {
            "id": next(menu_id_seq),
            "name": "Veggie Bowl",
            "price_cents": coerce_price("179"),
            "image": px("#C7F9CC"),
            "description": "Seasonal veggies, quinoa, tahini drizzle.",
        },
        {
            "id": next(menu_id_seq),
            "name": "Iced Latte",
            "price_cents": coerce_price("99"),
            "image": px("#FBCFE8"),
            "description": "Arabica espresso over ice and milk.",
        },
    ]
    MENU_DB.extend(sample_menu)

    SERVICE_DB.extend([
        {
            "id": next(service_id_seq),
            "name": "Event Place: Garden Pavilion",
            "price_cents": coerce_price("5000"),
            "image": px("#BFDBFE"),
        },
        {
            "id": next(service_id_seq),
            "name": "Event Place: Rooftop Lounge",
            "price_cents": coerce_price("8000"),
            "image": px("#C7F9CC"),
        },
    ])

@app.on_event("startup")
async def on_startup():
    seed_data()

@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/dashboard", status_code=302)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    reach = [120, 150, 180, 220, 260, 300, 340]
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "menu": MENU_DB,
            "price_fmt": price_fmt,
            "reach": reach,
        },
    )

@app.get("/manage", response_class=HTMLResponse)
async def manage(request: Request, msg: Optional[str] = None, err: Optional[str] = None):
    return templates.TemplateResponse(
        "manage.html",
        {
            "request": request,
            "menu": MENU_DB,
            "services": SERVICE_DB,
            "price_fmt": price_fmt,
            "msg": msg,
            "err": err,
        },
    )

@app.post("/menu")
async def add_menu(
    name: str = Form(...),
    price: str = Form(...),
    description: str = Form(""),
    image_file: UploadFile | None = File(default=None),
    image_url: Optional[str] = Form(None)
):
    try:
        price_cents = coerce_price(price)
    except ValueError as e:
        return RedirectResponse(url=f"/manage?err={e}", status_code=303)

    data_url = encode_upload_to_data_url(image_file) if image_file else None
    image = data_url or (image_url or "")

    item = {
        "id": next(menu_id_seq),
        "name": name.strip(),
        "price_cents": price_cents,
        "image": image,
        "description": description.strip(),
    }
    MENU_DB.append(item)
    return RedirectResponse(url="/manage?msg=Menu+added", status_code=303)

@app.get("/menu/{item_id}/edit", response_class=HTMLResponse)
async def edit_menu_form(request: Request, item_id: int):
    item = next((m for m in MENU_DB if m["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return templates.TemplateResponse("edit_menu.html", {"request": request, "item": item, "price_fmt": price_fmt})

@app.post("/menu/{item_id}/edit")
async def edit_menu(
    item_id: int,
    name: str = Form(...),
    price: str = Form(...),
    description: str = Form(""),
    image_file: UploadFile | None = File(default=None),
    image_url: Optional[str] = Form(None)
):
    item = next((m for m in MENU_DB if m["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    try:
        price_cents = coerce_price(price)
    except ValueError as e:
        return RedirectResponse(url=f"/menu/{item_id}/edit?err={e}", status_code=303)

    item["name"] = name.strip()
    item["price_cents"] = price_cents
    item["description"] = description.strip()

    data_url = encode_upload_to_data_url(image_file) if image_file else None
    if data_url:
        item["image"] = data_url
    elif image_url:
        item["image"] = image_url

    return RedirectResponse(url="/manage?msg=Menu+updated", status_code=303)

@app.post("/menu/{item_id}/delete")
async def delete_menu(item_id: int):
    idx = next((i for i, m in enumerate(MENU_DB) if m["id"] == item_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Menu item not found")
    del MENU_DB[idx]
    return RedirectResponse(url="/manage?msg=Menu+deleted", status_code=303)

@app.post("/services")
async def add_service(
    name: str = Form(...),
    price: str = Form(...),
    image_file: UploadFile | None = File(default=None)
):
    try:
        price_cents = coerce_price(price)
    except ValueError as e:
        return RedirectResponse(url=f"/manage?err={e}#services", status_code=303)

    data_url = encode_upload_to_data_url(image_file) if image_file else None
    image = data_url or ""

    item = {
        "id": next(service_id_seq),
        "name": name.strip(),
        "price_cents": price_cents,
        "image": image,
    }
    SERVICE_DB.append(item)
    return RedirectResponse(url="/manage?msg=Service+added#services", status_code=303)
