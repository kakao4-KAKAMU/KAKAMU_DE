import requests

import psycopg  # psycopg v3


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

limit = 500
offset = 0

query = f"""
select m.id, m.producing_year, m.nation, mg.genre, mt.title_name, ov.overview from 
(select m.id, m.producing_year, m.nation from movie as m
where m.is_rated and (m.is_adult is FALSE) and (producing_year is not null) and (tmdb_id is not null)
order by m.producing_year desc, m.id asc LIMIT {limit} offset {offset}) as m
left join (select mgr.movie_id, STRING_AGG(CAST(g.genre_name AS VARCHAR), ',') as genre from movie_genre_relation mgr
      left join genre g on mgr.genre_id = g.id
      group by mgr.movie_id) as mg on mg.movie_id = m.id
  left join overview ov on ov.movie_id = m.id
	left join movie_original_title as mt on m.id = mt.movie_id;
"""

def get_person_list(conn, movie_id):
    query_person = f"""
    select p.id, p.person_name, mpr.job from movie_person_relation as mpr
    left join person p on mpr.person_id = p.id
    where mpr.movie_id = '{movie_id}'
    """
    rows = execute_query(conn, query_person)
    return [{
        "person_id": str(row[0]),
        "name": row[1],
        "job": row[2],
    } for row in rows]

if __name__ == "__main__":
    conn = connect_to_postgres()
    with conn.cursor() as cur:
        rows = execute_query(cur, query)

        map_row = [dict(zip(["movie_id", "producing_year", "nation", "genres", "title", "plot"], row)) for row in rows]
        for row in map_row:
            persons = get_person_list(cur, row["movie_id"])
            response = requests.post(
                "http://localhost:8080/ingest/movie/regist",
                json={
                    "payload": {
                        "movie_id": str(row["movie_id"]),
                        "title": row["title"],
                        "producing_year": row["producing_year"],
                        "country": row["nation"] or None,
                        "genres": row["genres"].split(",") if row["genres"] else [],
                        "plot": row["plot"] or None,
                        "persons": persons,
                        "reviews": [],
                    }
                },
            )
            print(response.json())
