from fastapi import FastAPI, HTTPException


from db import get_db_connection
from data_loader import data_init



app = FastAPI()



def generate_sql_from_question(question, model):
    #dopo modello
    return ""






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
        conn=get_db_connection()
        cur=conn.cursor()
        cur.execute(
                """
               SELECT TABLE_NAME, COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                ORDER BY TABLE_NAME, ORDINAL_POSITION
                """
        )
        rows=cur.fetchall()
        cur.close()
        conn.close()

        result=[]
        for table_name, column_name in rows:
            result.append(
                {
                    "table_name": table_name,
                    "table_column": column_name
                }
            )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/search")
def search(body: dict):
    question=body.get("question", "")
    model= body.get("model")

    sql_query= generate_sql_from_question(question, model)
    return {
        "sql": sql_query,
        "sql_validation": "invalid",
        "results": None
    }

@app.post("/sql_search")
def sql_search(body: dict):
    sql_query=body.get("sql_query", "")
    if not isinstance(sql_query, str):
        return {
            "sql": "",
            "sql_validation": "invalid",
            "results": None
        }
    raw=sql_query.strip()
    lowered=raw.lower()

    unsafe_keywords=["insert", "update", "delete", "drop", "alter", "create", "truncate"]

    if not lowered.startswith("select") or any(k in lowered for k in unsafe_keywords):
        return {
            "sql": sql_query,
            "sql_validation": "unsafe",
            "results": None
        }
    
    try:
        conn=get_db_connection()
        cur=conn.cursor()
        cur.execute(sql_query)
        rows=cur.fetchall()
        description=cur.description or []
        cur.close()
        conn.close()
    except Exception:
        return {
            "sql": sql_query,
            "sql_validation": "invalid",
            "results": None
        }
    
    columns=[]

    for col in description:
        name= col[0]
        if isinstance(name, str):
            name=name.split(".")[-1]
        columns.append(name)
    
    if "from movies" in lowered:
        item_type= "film"
    else:
        item_type= "row"
    
    results=[]

    for row in rows:
        values=dict(zip(columns, row))
        name_value=None

        if "titolo" in values:
            name_value= values["titolo"]
        elif "nome" in values:
            name_value=values["nome"]
        elif columns:
            name_value=row[0]
    
        properties=[]

        if name_value is not None:
            properties.append(
                {
                    "property_name": "name",
                    "property_value": name_value
                }
            )
    
        for col_name, val in values.items():
            if col_name in ("titolo", "nome"):
                continue
            properties.append(
                {
                    "property_name": col_name,
                    "property_value": val
                }
            )
    
        results.append(
            {
                "item_type": item_type,
                "properties": properties
            }
        )

    return {
        "sql": sql_query,
        "sql_validation": "valid",
        "results": results
    }