import requests
import psycopg
import sys

def connect_to_postgres():
    try:
        conn = psycopg.connect(
            host="127.0.0.1",
            port=5433,
            dbname="chatbot",
            user="postgres",
            password="postgres",
        )
        return conn
    except Exception as e:
        print(f"❌ DB 연결 실패: {e}")
        sys.exit(1)

def execute_query(conn, query):
    with conn.cursor() as cur:
        cur.execute(query)
        return cur.fetchall()

limit = 500
offset = 500

# query = f"""
# select m.id, m.producing_year, m.nation, mg.genre, mt.title_name, ov.overview from 
# (select m.id, m.producing_year, m.nation from movie as m
# where m.is_rated and (m.is_adult is FALSE) and (producing_year is not null) and (tmdb_id is not null)
# order by m.producing_year desc, m.id asc LIMIT {limit} offset {offset}) as m
# left join (select mgr.movie_id, STRING_AGG(CAST(g.genre_name AS VARCHAR), ',') as genre from movie_genre_relation mgr
#       left join genre g on mgr.genre_id = g.id
#       group by mgr.movie_id) as mg on mg.movie_id = m.id
#   left join overview ov on ov.movie_id = m.id
#     left join movie_original_title as mt on m.id = mt.movie_id;
# """

query = f"""
select m.id, m.producing_year, m.nation, mg.genre, mt.title_name, ov.overview from 
(
    -- 1. 조건에 맞는 영화 500개 먼저 추출
    select m.id, m.producing_year, m.nation from movie as m
    where m.is_rated and (m.is_adult is FALSE) and (producing_year is not null) and (tmdb_id is not null)
    order by m.producing_year desc, m.id asc 
    LIMIT {limit} offset {offset}
) as m
left join (
    -- 2. 장르 데이터를 쉼표(,)로 묶어서 한 줄로 조립
    select mgr.movie_id, STRING_AGG(CAST(g.genre_name AS VARCHAR), ',') as genre 
    from movie_genre_relation mgr
    left join genre g on mgr.genre_id = g.id
    group by mgr.movie_id
) as mg on mg.movie_id = m.id
left join overview ov on ov.movie_id = m.id
left join (
    -- 3. ★ 핵심: 영화 ID당 제목을 딱 하나만 골라내어 중복 조인 방지
    SELECT DISTINCT ON (movie_id) movie_id, title_name 
    FROM movie_title
) as mt on m.id = mt.movie_id;
"""

if __name__ == "__main__":
    print("🚀 스크립트 시작: DB 연결 중...")
    conn = connect_to_postgres()
    try:
        rows = execute_query(conn, query)
        print(f"✅ DB 조회 성공! 데이터 건수: {len(rows)}건")
        
        if len(rows) == 0:
            print("⚠️ 데이터가 없습니다. 쿼리 조건을 확인하세요.")
            sys.exit(0)

        map_row = [dict(zip(["movie_id", "producing_year", "nation", "genres", "title", "plot"], row)) for row in rows]
        
        for i, row in enumerate(map_row):
            response = requests.post("http://localhost:8080/ingest/movie/regist", json={
              "payload": {
                "movie_id": str(row["movie_id"]),
                "title": row["title"],
                "producing_year": row["producing_year"],
                "country": row["nation"] or None,
                "genres": row["genres"].split(",") if row["genres"] else [],
                "plot": row["plot"] or None,
              } 
            })
            
            if response.status_code == 200:
                print(f"[{i+1}/{len(map_row)}] 전송 성공: {row['title']}")
            else:
                print(f"[{i+1}/{len(map_row)}] 전송 실패 ({response.status_code}): {row['title']}")
                
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
    finally:
        conn.close()
        print("🏁 작업 종료.")