import os

import requests
from fastapi import FastAPI, HTTPException

from db import get_db_connection
from data_loader import data_init

app = FastAPI()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434/api/chat")
DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "gemma3:1b-it-qat")


def build_schema_description():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT TABLE_NAME, COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        ORDER BY TABLE_NAME, ORDINAL_POSITION
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    lines = []
    current_table = None

    for table_name, column_name in rows:
        if table_name != current_table:
            lines.append(f"Tabella {table_name}:")
            current_table = table_name
        lines.append(f"- {column_name}")

    return "\n".join(lines)


def call_ollama(prompt, model_name):
    model = model_name or DEFAULT_LLM_MODEL

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "stream": False,
    }

    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    message = data.get("message", {})
    content = message.get("content", "")

    if not isinstance(content, str):
        return ""

    return content


def clean_sql_response(text):
    sql = text.strip()

    if "```" in sql:
        parts = sql.split("```")
        if len(parts) >= 2:
            sql = parts[1]

    sql = sql.strip()
    idx = sql.lower().find("select")

    if idx != -1:
        sql = sql[idx:]

    if ";" in sql:
        sql = sql.split(";")[0] + ";"

    return sql.strip()


def generate_sql_from_question(question, model):
    if not isinstance(question, str) or not question.strip():
        return ""

    schema_text = build_schema_description()

    prompt = (
        "Sei un assistente che traduce domande in una singola query SQL SELECT per MariaDB.\n"
        "Non usare mai comandi che modificano il database (niente INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE).\n"
        "Puoi usare solo le tabelle e le colonne presenti nello schema seguente.\n\n"
        f"{schema_text}\n\n"
        f"Domanda: {question}\n"
        "Rispondi solo con la query SQL."
    )

    try:
        raw_answer = call_ollama(prompt, model)
    except Exception as e:
        print("Errore chiamando Ollama:", e)
        return ""

    return clean_sql_response(raw_answer)


def run_sql_query(sql_query):
    if not isinstance(sql_query, str):
        return "invalid", None

    raw = sql_query.strip()
    lowered = raw.lower()

    unsafe_keywords = ["insert", "update", "delete", "drop", "alter", "create", "truncate"]

    if not lowered.startswith("select") or any(k in lowered for k in unsafe_keywords):
        return "unsafe", None

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(sql_query)
        rows = cur.fetchall()
        description = cur.description or []
        cur.close()
        conn.close()
    except Exception:
        return "invalid", None

    columns = []

    for col in description:
        name = col[0]
        if isinstance(name, str):
            name = name.split(".")[-1]
        columns.append(name)

    if "from movies" in lowered:
        item_type = "film"
    else:
        item_type = "row"

    results = []

    for row in rows:
        values = dict(zip(columns, row))
        name_value = None

        if "titolo" in values:
            name_value = values["titolo"]
        elif "nome" in values:
            name_value = values["nome"]
        elif columns:
            name_value = row[0]

        properties = []

        if name_value is not None:
            properties.append(
                {
                    "property_name": "name",
                    "property_value": name_value,
                }
            )

        for col_name, val in values.items():
            if col_name in ("titolo", "nome"):
                continue
            properties.append(
                {
                    "property_name": col_name,
                    "property_value": val,
                }
            )

        results.append(
            {
                "item_type": item_type,
                "properties": properties,
            }
        )

    return "valid", results


def run_sql_query_with_error(sql_query):
    if not isinstance(sql_query, str):
        return "invalid", None, "La query non è una stringa."

    raw = sql_query.strip()
    lowered = raw.lower()

    unsafe_keywords = ["insert", "update", "delete", "drop", "alter", "create", "truncate"]

    if not lowered.startswith("select") or any(k in lowered for k in unsafe_keywords):
        return "unsafe", None, "La query non è una SELECT sicura."

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(sql_query)
        rows = cur.fetchall()
        description = cur.description or []
        cur.close()
        conn.close()
    except Exception as e:
        return "invalid", None, str(e)

    columns = []

    for col in description:
        name = col[0]
        if isinstance(name, str):
            name = name.split(".")[-1]
        columns.append(name)

    if "from movies" in lowered:
        item_type = "film"
    else:
        item_type = "row"

    results = []

    for row in rows:
        values = dict(zip(columns, row))
        name_value = None

        if "titolo" in values:
            name_value = values["titolo"]
        elif "nome" in values:
            name_value = values["nome"]
        elif columns:
            name_value = row[0]

        properties = []

        if name_value is not None:
            properties.append(
                {
                    "property_name": "name",
                    "property_value": name_value,
                }
            )

        for col_name, val in values.items():
            if col_name in ("titolo", "nome"):
                continue
            properties.append(
                {
                    "property_name": col_name,
                    "property_value": val,
                }
            )

        results.append(
            {
                "item_type": item_type,
                "properties": properties,
            }
        )

    return "valid", results, ""



@app.on_event("startup")
def startup_event():
    try:
        data_init()
    except Exception as e:
        print("Errore durante data_init:", e)


@app.get("/ping")
def ping():
    return {"message": "pong"}


@app.get("/db-test")
def db_test():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SHOW TABLES;")
        tables = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        return tables
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/schema_summary")
def schema_summary():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT TABLE_NAME, COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            ORDER BY TABLE_NAME, ORDINAL_POSITION
            """
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        result = []
        for table_name, column_name in rows:
            result.append(
                {
                    "table_name": table_name,
                    "table_column": column_name,
                }
            )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search")
def search(body: dict):
    question = body.get("question", "")
    model = body.get("model")

    sql_query = generate_sql_from_question(question, model)

    if not isinstance(sql_query, str) or not sql_query.strip():
        return {
            "sql": sql_query,
            "sql_validation": "invalid",
            "results": None,
        }

    validation, results = run_sql_query(sql_query)

    if validation != "valid":
        results_to_return = None
    else:
        results_to_return = results

    return {
        "sql": sql_query,
        "sql_validation": validation,
        "results": results_to_return,
    }


@app.post("/sql_search")
def sql_search(body: dict):
    sql_query = body.get("sql_query", "")

    validation, results = run_sql_query(sql_query)

    if validation != "valid":
        results_to_return = None
    else:
        results_to_return = results

    return {
        "sql": sql_query,
        "sql_validation": validation,
        "results": results_to_return,
    }

@app.post("/add")
def add(body: dict):
    data_line = body.get("data_line")

    if not isinstance(data_line, str):
        raise HTTPException(status_code=422, detail="data_line must be a string")

    parts = [p.strip() for p in data_line.split(",")]

    if len(parts) != 7:
        raise HTTPException(status_code=422, detail="Invalid data_line format")

    titolo, regista, eta_autore_str, anno_str, genere, piattaforma_1, piattaforma_2 = parts

    if not titolo or not regista:
        raise HTTPException(status_code=422, detail="Title and director must be non-empty")

    try:
        eta_autore = int(eta_autore_str)
        anno = int(anno_str)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid numeric value")

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT id FROM directors WHERE nome = ?;", (regista,))
        r = cur.fetchone()
        if r:
            director_id = r[0]
            cur.execute("UPDATE directors SET eta = ? WHERE id = ?;", (eta_autore, director_id))
        else:
            cur.execute("INSERT INTO directors (nome, eta) VALUES (?, ?);", (regista, eta_autore))
            director_id = cur.lastrowid

        cur.execute("SELECT id FROM movies WHERE titolo = ?;", (titolo,))
        r = cur.fetchone()
        if r:
            movie_id = r[0]
            cur.execute(
                "UPDATE movies SET anno = ?, genere = ?, director_id = ? WHERE id = ?;",
                (anno, genere, director_id, movie_id),
            )
        else:
            cur.execute(
                "INSERT INTO movies (titolo, anno, genere, director_id) VALUES (?, ?, ?, ?);",
                (titolo, anno, genere, director_id),
            )
            movie_id = cur.lastrowid

        cur.execute("DELETE FROM movie_platform WHERE movie_id = ?;", (movie_id,))

        piattaforme = []
        if piattaforma_1:
            piattaforme.append(piattaforma_1)
        if piattaforma_2:
            piattaforme.append(piattaforma_2)

        for nome_p in piattaforme:
            cur.execute("SELECT id FROM platforms WHERE nome = ?;", (nome_p,))
            r = cur.fetchone()
            if r:
                platform_id = r[0]
            else:
                cur.execute("INSERT INTO platforms (nome) VALUES (?);", (nome_p,))
                platform_id = cur.lastrowid

            cur.execute(
                "INSERT INTO movie_platform (movie_id, platform_id) VALUES (?, ?);",
                (movie_id, platform_id),
            )

        conn.commit()
        cur.close()
        conn.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "ok"}


@app.post("/search_with_retry")
def search_with_retry(body: dict):
    question = body.get("question", "")
    model = body.get("model")

    sql_query_1 = generate_sql_from_question(question, model)

    if not isinstance(sql_query_1, str) or not sql_query_1.strip():
        validation_1 = "invalid"
        results_1 = None
        error_message_1 = "La query generata è vuota."
    else:
        validation_1, results_1, error_message_1 = run_sql_query_with_error(sql_query_1)

    if validation_1 != "valid":
        results_1_to_return = None
    else:
        results_1_to_return = results_1

    attempt_1 = {
        "sql": sql_query_1,
        "sql_validation": validation_1,
        "results": results_1_to_return,
    }

    attempt_2 = None

    if validation_1 != "valid":
        schema_text = build_schema_description()
        error_text = error_message_1 or "La query non è stata eseguita con successo."

        retry_prompt = (
            "Ti mostro lo schema del database, una domanda in linguaggio naturale, "
            "una query SQL che non ha funzionato e il messaggio di errore.\n"
            "Correggi la query scrivendo una nuova query SQL SELECT per MariaDB che risponda alla domanda, "
            "usando solo lo schema dato.\n\n"
            "Schema del database:\n"
            f"{schema_text}\n\n"
            "Domanda originale:\n"
            f"{question}\n\n"
            "Query SQL precedente:\n"
            f"{sql_query_1}\n\n"
            "Messaggio di errore del database o del sistema:\n"
            f"{error_text}\n\n"
            "Rispondi solo con la query SQL."
        )

        try:
            raw_answer_2 = call_ollama(retry_prompt, model)
            sql_query_2 = clean_sql_response(raw_answer_2)
        except Exception as e:
            print("Errore chiamando Ollama per retry:", e)
            sql_query_2 = ""

        if not isinstance(sql_query_2, str) or not sql_query_2.strip():
            attempt_2 = {
                "sql": sql_query_2,
                "sql_validation": "invalid",
                "results": None,
            }
        else:
            validation_2, results_2, error_message_2 = run_sql_query_with_error(sql_query_2)

            if validation_2 != "valid":
                results_2_to_return = None
            else:
                results_2_to_return = results_2

            attempt_2 = {
                "sql": sql_query_2,
                "sql_validation": validation_2,
                "results": results_2_to_return,
            }

    return {
        "attempt_1": attempt_1,
        "attempt_2": attempt_2,
    }
