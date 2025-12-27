import os
import json

import requests
from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates

app = FastAPI()

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

templates = Jinja2Templates(directory="templates")


def base_context(request: Request):
    return {
        "request": request,
        "schema_json": "",
        "sql_search_sql": "",
        "sql_search_json": "",
        "search_question": "",
        "search_model": "",
        "search_sql": "",
        "search_json": "",
        "search_retry_question": "",
        "search_retry_model": "",
        "search_retry_json": "",
        "add_line": "",
        "add_status": "",
    }


def call_backend(method, path, payload=None):
    url = BACKEND_URL + path
    response = requests.request(method, url, json=payload, timeout=60)
    try:
        data = response.json()
    except ValueError:
        data = response.text
    return response.status_code, data


@app.get("/")
def index(request: Request):
    context = base_context(request)
    return templates.TemplateResponse("index.html", context)


@app.post("/schema_summary")
def ui_schema_summary(request: Request):
    context = base_context(request)
    status, data = call_backend("GET", "/schema_summary")

    if status == 200:
        context["schema_json"] = json.dumps(data, ensure_ascii=False, indent=2)
    else:
        context["schema_json"] = f"Errore {status}: {data}"

    return templates.TemplateResponse("index.html", context)


@app.post("/sql_search")
def ui_sql_search(request: Request, sql_query: str = Form(default="")):
    context = base_context(request)
    context["sql_search_sql"] = sql_query

    if sql_query.strip():
        status, data = call_backend("POST", "/sql_search", {"sql_query": sql_query})
        if isinstance(data, dict):
            context["sql_search_json"] = json.dumps(data, ensure_ascii=False, indent=2)
        else:
            context["sql_search_json"] = f"Errore {status}: {data}"

    return templates.TemplateResponse("index.html", context)


@app.post("/search")
def ui_search(
    request: Request,
    question: str = Form(default=""),
    model: str = Form(default=""),
):
    context = base_context(request)
    context["search_question"] = question
    context["search_model"] = model

    payload = {"question": question}
    if model.strip():
        payload["model"] = model.strip()

    if question.strip():
        status, data = call_backend("POST", "/search", payload)
        if isinstance(data, dict):
            context["search_sql"] = data.get("sql") or ""
            context["search_json"] = json.dumps(data, ensure_ascii=False, indent=2)
        else:
            context["search_json"] = f"Errore {status}: {data}"

    return templates.TemplateResponse("index.html", context)


@app.post("/search_with_retry")
def ui_search_with_retry(
    request: Request,
    question: str = Form(default=""),
    model: str = Form(default=""),
):
    context = base_context(request)
    context["search_retry_question"] = question
    context["search_retry_model"] = model

    payload = {"question": question}
    if model.strip():
        payload["model"] = model.strip()

    if question.strip():
        status, data = call_backend("POST", "/search_with_retry", payload)
        if isinstance(data, dict):
            context["search_retry_json"] = json.dumps(
                data, ensure_ascii=False, indent=2
            )
        else:
            context["search_retry_json"] = f"Errore {status}: {data}"

    return templates.TemplateResponse("index.html", context)


@app.post("/add")
def ui_add(
    request: Request,
    data_line: str = Form(default=""),
):
    context = base_context(request)
    context["add_line"] = data_line

    if data_line.strip():
        status, data = call_backend("POST", "/add", {"data_line": data_line})
        if status == 200:
            context["add_status"] = "Film salvato correttamente"
        else:
            if isinstance(data, dict) and "detail" in data:
                context["add_status"] = f"Errore {status}: {data['detail']}"
            else:
                context["add_status"] = f"Errore {status}: {data}"

    return templates.TemplateResponse("index.html", context)
