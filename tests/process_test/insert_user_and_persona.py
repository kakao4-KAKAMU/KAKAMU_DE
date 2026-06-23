import requests

import psycopg  # psycopg v3

INGEST_BASE_URL = "http://localhost:8080"


def connect_to_postgres():
    conn = psycopg.connect(
        host="localhost",
        port=5432,
        dbname="postgres",
        user="postgres",
        password="mysecretpassword",
    )
    return conn


def execute_query(cur, query):
    cur.execute(query)
    return cur.fetchall()


user_query = """
select nickname, id, created_at from "user";
"""

persona_query = """
select nickname, persona_type, profile_image_url, status, id, user_id from persona;
"""


def persona_movie_query(persona_id):
    return f"""
select persona_id, movie_id from fav_movie where persona_id = '{persona_id}';
"""


def persona_person_query(persona_id):
    return f"""
select persona_id, people_id from fav_people where persona_id = '{persona_id}';
"""


def persona_genre_query(persona_id):
    return f"""
select fg.persona_id, g.genre_name
from fav_genre fg
left join genre g on fg.genre_id = g.id
where fg.persona_id = '{persona_id}';
"""


def _serialize_datetime(value):
    if value is None:
        return None
    return value.isoformat()


def get_users(cur):
    rows = execute_query(cur, user_query)
    return [
        {
            "user_id": str(row[1]),
            "nickname": row[0],
            "created_at": row[2],
        }
        for row in rows
    ]


def get_personas(cur):
    rows = execute_query(cur, persona_query)
    return [
        {
            "persona_id": str(row[4]),
            "user_id": str(row[5]),
            "label": row[0],
            "persona_type": row[1],
            "profile_image_url": row[2],
            "status": row[3],
        }
        for row in rows
    ]


def get_persona_movies(cur, persona_id):
    rows = execute_query(cur, persona_movie_query(persona_id))
    return [str(row[1]) for row in rows]


def get_persona_persons(cur, persona_id):
    rows = execute_query(cur, persona_person_query(persona_id))
    return [str(row[1]) for row in rows]


def get_persona_genres(cur, persona_id):
    rows = execute_query(cur, persona_genre_query(persona_id))
    return [row[1] for row in rows if row[1]]


def ingest_user(user):
    response = requests.post(
        f"{INGEST_BASE_URL}/ingest/user/regist",
        json={
            "payload": {
                "user_id": user["user_id"],
                "nickname": user["nickname"],
                "created_at": _serialize_datetime(user["created_at"]),
            }
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def ingest_persona(persona, *, movies, persons, genres):
    response = requests.post(
        f"{INGEST_BASE_URL}/ingest/persona/create",
        json={
            "payload": {
                "persona_id": persona["persona_id"],
                "user_id": persona["user_id"],
                "label": persona["label"],
                "genres": genres,
                "movies": movies,
                "persons": persons,
            }
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    conn = connect_to_postgres()
    with conn.cursor() as cur:
        users = get_users(cur)
        for user in users:
            result = ingest_user(user)
            print(f"user {user['user_id']}: {result}")

        personas = get_personas(cur)
        for persona in personas:
            persona_id = persona["persona_id"]
            movies = get_persona_movies(cur, persona_id)
            persons = get_persona_persons(cur, persona_id)
            genres = get_persona_genres(cur, persona_id)
            result = ingest_persona(
                persona,
                movies=movies,
                persons=persons,
                genres=genres,
            )
            print(
                f"persona {persona_id} "
                f"(movies={len(movies)}, persons={len(persons)}, genres={len(genres)}): "
                f"{result}"
            )
