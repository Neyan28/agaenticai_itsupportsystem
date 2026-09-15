import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def create_ticket(user_query: str) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tickets (user_query, status) VALUES (%s, 'open') RETURNING ticket_id",
        (user_query,)
    )
    ticket_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return ticket_id


def get_ticket(ticket_id: int) -> dict:
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM tickets WHERE ticket_id = %s", (ticket_id,))
    ticket = cur.fetchone()
    cur.close()
    conn.close()
    return dict(ticket) if ticket else None


def update_ticket_status(ticket_id: int, status: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE tickets SET status = %s WHERE ticket_id = %s",
        (status, ticket_id)
    )
    conn.commit()
    cur.close()
    conn.close()


def update_ticket_solution(ticket_id: int, solution: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE tickets SET solution = %s WHERE ticket_id = %s",
        (solution, ticket_id)
    )
    conn.commit()
    cur.close()
    conn.close()


def assign_ticket(ticket_id: int, member_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE tickets SET assigned_to = %s, status = 'pending_it' WHERE ticket_id = %s",
        (member_id, ticket_id)
    )
    conn.commit()
    cur.close()
    conn.close()


def resolve_ticket(ticket_id: int, solution: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """UPDATE tickets
           SET status = 'resolved', solution = %s, resolved_at = NOW()
           WHERE ticket_id = %s""",
        (solution, ticket_id)
    )
    conn.commit()
    cur.close()
    conn.close()


def get_tickets_for_member(member_id: int) -> list:
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT * FROM tickets WHERE assigned_to = %s AND status = 'pending_it'",
        (member_id,)
    )
    tickets = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(t) for t in tickets]


def get_all_members() -> list:
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM it_members ORDER BY member_id")
    members = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(m) for m in members]


def get_least_busy_member() -> dict:
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT * FROM it_members ORDER BY active_tickets ASC LIMIT 1"
    )
    member = cur.fetchone()
    cur.close()
    conn.close()
    return dict(member) if member else None


def increment_workload(member_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE it_members SET active_tickets = active_tickets + 1 WHERE member_id = %s",
        (member_id,)
    )
    conn.commit()
    cur.close()
    conn.close()


def decrement_workload(member_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE it_members SET active_tickets = GREATEST(active_tickets - 1, 0) WHERE member_id = %s",
        (member_id,)
    )
    conn.commit()
    cur.close()
    conn.close()
