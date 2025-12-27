import csv
from pathlib import Path
from db import get_db_connection

DATA_FILE_PATH = Path("/app/data.tsv")

def data_init():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM movies;")
    (count_movies,) = cur.fetchone()

    if count_movies > 0:
        cur.close()
        conn.close()
        return

    if not DATA_FILE_PATH.exists():
        cur.close()
        conn.close()
        raise FileNotFoundError("data.tsv non trovato")

    with DATA_FILE_PATH.open(encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:
            titolo = row["Titolo"].strip()
            regista = row["Regista"].strip()
            eta_autore = int(row["Età_Autore"])
            anno = int(row["Anno"])
            genere = row["Genere"].strip()
            p1 = row["Piattaforma_1"].strip()
            p2 = row["Piattaforma_2"].strip()

            cur.execute("SELECT id FROM directors WHERE nome = ?;", (regista,))
            r = cur.fetchone()
            if r:
                director_id = r[0]
            else:
                cur.execute("INSERT INTO directors (nome, eta) VALUES (?, ?);", (regista, eta_autore))
                director_id = cur.lastrowid

            cur.execute("SELECT id FROM movies WHERE titolo = ?;", (titolo,))
            r = cur.fetchone()
            if r:
                movie_id = r[0]
            else:
                cur.execute(
                    "INSERT INTO movies (titolo, anno, genere, director_id) VALUES (?, ?, ?, ?);",
                    (titolo, anno, genere, director_id)
                )
                movie_id = cur.lastrowid

            piattaforme = []
            if p1:
                piattaforme.append(p1)
            if p2:
                piattaforme.append(p2)

            for nome_p in piattaforme:
                cur.execute("SELECT id FROM platforms WHERE nome = ?;", (nome_p,))
                r = cur.fetchone()
                if r:
                    platform_id = r[0]
                else:
                    cur.execute("INSERT INTO platforms (nome) VALUES (?);", (nome_p,))
                    platform_id = cur.lastrowid

                cur.execute(
                    "INSERT IGNORE INTO movie_platform (movie_id, platform_id) VALUES (?, ?);",
                    (movie_id, platform_id)
                )

    conn.commit()
    cur.close()
    conn.close()
