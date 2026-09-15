import json
import os
import sys
import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI
from dotenv import load_dotenv
from langgraph.types import interrupt

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.state import TicketState
from db.postgres import (
    get_least_busy_member, assign_ticket, increment_workload,
    resolve_ticket, decrement_workload
)

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
CHROMA_PERSIST_PATH = os.getenv("CHROMA_PERSIST_PATH", "./chroma_store")


def call_openai(prompt: str, system: str = None) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=1024
    )
    return response.choices[0].message.content


def get_chroma_collection():
    chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_PATH)
    embedding_fn = embedding_functions.DefaultEmbeddingFunction()
    return chroma_client.get_or_create_collection(
        name="it_solutions",
        embedding_function=embedding_fn
    )


# ─── NODE 1: understand_ticket ────────────────────────────────────

def understand_ticket(state: TicketState) -> TicketState:
    prompt = f"""
A user has raised the following IT support ticket:

"{state['user_query']}"

Acknowledge that you have received the ticket and briefly describe what kind of
IT issue this is in one sentence. Be concise and professional.
"""
    response = call_openai(prompt, system="You are a helpful IT support agent.")
    print(f"[understand_ticket] {response}")
    return {**state, "status": "open"}


# ─── NODE 2: query_chromadb ───────────────────────────────────────

def query_chromadb(state: TicketState) -> TicketState:
    collection = get_chroma_collection()
    try:
        results = collection.query(query_texts=[state["user_query"]], n_results=1)
        if results["documents"] and results["documents"][0]:
            best_distance = results["distances"][0][0]
            best_solution = results["documents"][0][0]
            if best_distance <= 0.3:
                return {**state, "solution": best_solution, "solution_source": "chromadb"}
    except Exception as e:
        print(f"[query_chromadb] error: {e}")
    return {**state, "solution": None, "solution_source": None}


# ─── NODE 3: route_to_it ──────────────────────────────────────────

def route_to_it(state: TicketState) -> TicketState:
    member = get_least_busy_member()
    if member:
        assign_ticket(state["ticket_id"], member["member_id"])
        increment_workload(member["member_id"])
        return {
            **state,
            "assigned_to": member["member_id"],
            "assigned_name": member["name"],
            "status": "pending_it"
        }
    return {**state, "status": "pending_it"}


# ─── NODE 4: wait_for_it_solution ────────────────────────────────

def wait_for_it_solution(state: TicketState) -> TicketState:
    it_solution = interrupt({
        "ticket_id": state["ticket_id"],
        "user_query": state["user_query"],
        "assigned_to": state.get("assigned_to"),
        "assigned_name": state.get("assigned_name"),
        "message": "Waiting for IT member to submit solution"
    })
    return {**state, "solution": it_solution, "solution_source": "it_member"}


# ─── NODE 5: store_solution ───────────────────────────────────────

def store_solution(state: TicketState) -> TicketState:
    collection = get_chroma_collection()
    try:
        collection.add(
            documents=[state["solution"]],
            metadatas=[{
                "ticket_id": str(state["ticket_id"]),
                "user_query": state["user_query"]
            }],
            ids=[f"ticket_{state['ticket_id']}"]
        )
        print(f"[store_solution] stored ticket_{state['ticket_id']}")
    except Exception as e:
        print(f"[store_solution] error: {e}")
    return {**state}


# ─── NODE 6: close_ticket ─────────────────────────────────────────

def close_ticket(state: TicketState) -> TicketState:
    resolve_ticket(state["ticket_id"], state["solution"])
    if state.get("assigned_to"):
        decrement_workload(state["assigned_to"])
    print(f"[close_ticket] ticket_{state['ticket_id']} resolved")
    return {**state, "status": "resolved"}


# ─── CONDITIONAL EDGES ───────────────────────────────────────────

def check_solution_found(state: TicketState) -> str:
    return "solution_found" if state.get("solution") else "no_solution"


def check_user_feedback(state: TicketState) -> str:
    return "worked" if state.get("user_feedback") == "worked" else "not_worked"
