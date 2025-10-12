import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def display_results(results, columns, title):
    if not results:
        print(f"{title}: No results found, womp womp")
        return

    print(f"{title}")
    print("=" * 80)

    for i, row in enumerate(results, 1):
        print(f"{i}. Result:")
        for col_name, value in zip(columns, row):
            # Format specific columns nicely
            if col_name == "embedding_distance":
                print(f"   {col_name.replace('_', ' ').title()}: {value:.6f}")
            elif col_name in ["start_time", "end_time"]:
                print(f"   {col_name.replace('_', ' ').title()}: {value}s")
            elif col_name == "segment_raw_text":
                print(f"   Content: {value}")
            else:
                print(f"   {col_name.replace('_', ' ').title()}: {value}")
        print("-" * 80)


def find_similar_segments(cursor, segment_id, similar=True):
    order = "ASC" if similar else "DESC"

    query = """
    SELECT 
      p.title AS podcast_name,
      ps.id AS segment_id,
      ps.content AS segment_raw_text,
      ps.start_time,
      ps.end_time,
      ps.embedding <-> target.embedding AS embedding_distance
    FROM podcast_segment ps
    INNER JOIN podcast p 
      ON ps.podcast_id = p.id
    CROSS JOIN (
      SELECT embedding 
      FROM podcast_segment 
      WHERE id = %s
    ) AS target
    WHERE ps.id != %s
    ORDER BY ps.embedding <-> target.embedding {}
    LIMIT 5
    """.format(
        order
    )

    cursor.execute(query, (segment_id, segment_id))
    return cursor.fetchall()


def find_similar_episode_by_segment_id(cursor, segment_id):
    query = """
    WITH target AS (
      SELECT embedding
      FROM podcast_segment
      WHERE id = %s
    ),
    average_podcast_embedding AS (
      SELECT podcast_id, AVG(embedding) AS embedding
      FROM podcast_segment
      GROUP BY podcast_id
    )

    SELECT 
      p.title AS podcast_title, 
      target.embedding <-> ape.embedding AS embedding_distance
    FROM average_podcast_embedding ape 
    INNER JOIN podcast p
      ON ape.podcast_id = p.id
    CROSS JOIN target
    WHERE ape.podcast_id != (
      SELECT podcast_id
      FROM podcast_segment
      WHERE id = %s
    )
    ORDER BY target.embedding <-> ape.embedding
    LIMIT 5
    """

    cursor.execute(query, (segment_id, segment_id))
    return cursor.fetchall()


def find_similar_episode_by_episode_id(cursor, episode_id):
    query = """
    WITH target AS (
      SELECT embedding
      FROM podcast_segment
      WHERE podcast_id = %s
    ),
    average_podcast_embedding AS (
      SELECT podcast_id, AVG(embedding) AS embedding
      FROM podcast_segment
      GROUP BY podcast_id
    )

    SELECT 
      p.title AS podcast_title, 
      target.embedding <-> ape.embedding AS embedding_distance
    FROM average_podcast_embedding ape 
    INNER JOIN podcast p
      ON ape.podcast_id = p.id
    CROSS JOIN target
    WHERE ape.podcast_id != %s
    ORDER BY target.embedding <-> ape.embedding
    LIMIT 5
    """

    cursor.execute(query, (episode_id, episode_id))
    return cursor.fetchall()


CONNECTION = os.getenv("TIMESCALE_CONNECTION_STRING")

conn = psycopg2.connect(CONNECTION)
cursor = conn.cursor()

columns = [
    "podcast_name",
    "segment_id",
    "segment_raw_text",
    "start_time",
    "end_time",
    "embedding_distance",
]

"""
The questions below are the source of where these queries came from.

Q1) What are the five most similar segments to segment "267:476"

Input: "that if we were to meet alien life at some point"
For each result return the podcast name, the segment id, segment raw text,  the start time, stop time, and embedding distance

Q2) What are the five most dissimilar segments to segment "267:476"

Input: "that if we were to meet alien life at some point"
For each result return the podcast name, the segment id, segment raw text,  the start time, stop time, and embedding distance

Q3) What are the five most similar segments to segment '48:511'

Input: "Is it is there something especially interesting and profound to you in terms of our current deep learning neural network, artificial neural network approaches and the whatever we do understand about the biological neural network."
For each result return the podcast name, the segment id, segment raw text,  the start time, stop time, and embedding distance

Q4) What are the five most similar segments to segment '51:56'

Input: "But what about like the fundamental physics of dark energy? Is there any understanding of what the heck it is?"
For each result return the podcast name, the segment id, segment raw text,  the start time, stop time, and embedding distance

Q5) For each of the following podcast segments, find the five most similar podcast episodes. Hint: You can do this by averaging over the embedding vectors within a podcast episode.

    a) Segment "267:476"

    b) Segment '48:511'

    c) Segment '51:56'

For each result return the Podcast title and the embedding distance

Q6) For podcast episode id = VeH7qKZr0WI, find the five most similar podcast episodes. Hint: you can do a similar averaging procedure as Q5

Input Episode: "Balaji Srinivasan: How to Fix Government, Twitter, Science, and the FDA | Lex Fridman Podcast #331"
For each result return the Podcast title and the embedding distance
"""

q1_results = find_similar_segments(cursor, "267:476")
display_results(q1_results, columns, "Query 1")

q2_results = find_similar_segments(cursor, "267:476", False)
display_results(q2_results, columns, "Query 2")

q3_results = find_similar_segments(cursor, "48:511")
display_results(q3_results, columns, "Query 3")

q4_results = find_similar_segments(cursor, "51:56")
display_results(q4_results, columns, "Query 4")

columns = ["podcast_title", "embedding_distance"]
q5a_results = find_similar_episode_by_segment_id(cursor, "267:476")
display_results(q5a_results, columns, "Query 5A")

q5b_results = find_similar_episode_by_segment_id(cursor, "48:511")
display_results(q5b_results, columns, "Query 5B")

q5c_results = find_similar_episode_by_segment_id(cursor, "51:56")
display_results(q5c_results, columns, "Query 5C")

q6_results = find_similar_episode_by_episode_id(cursor, "VeH7qKZr0WI")
display_results(q6_results, columns, "Query 6")

conn.commit()
conn.close()
