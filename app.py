import streamlit as st
import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db.postgres import create_ticket, get_ticket, get_least_busy_member, assign_ticket, increment_workload
from agent.graph import start_ticket, get_ticket_state, set_user_feedback

load_dotenv()

st.set_page_config(page_title="IT Support Portal", layout="centered")
st.title(" IT Support Portal")
st.caption("Raise a ticket and our AI agent will help you instantly.")

if "ticket_id" not in st.session_state:
    st.session_state.ticket_id = None
if "ticket_state" not in st.session_state:
    st.session_state.ticket_state = None
if "stage" not in st.session_state:
    st.session_state.stage = "input"


# ─── STAGE 1: INPUT ───────────────────────────────────────────────

if st.session_state.stage == "input":
    st.subheader("Describe your IT problem")
    user_query = st.text_area(
        "What issue are you facing?",
        placeholder="e.g. My laptop won't connect to the office WiFi...",
        height=120
    )
    if st.button("Submit Ticket", type="primary"):
        if not user_query.strip():
            st.warning("Please describe your problem before submitting.")
        else:
            with st.spinner("AI agent is working on your ticket..."):
                ticket_id = create_ticket(user_query.strip())
                st.session_state.ticket_id = ticket_id
                result = start_ticket(ticket_id, user_query.strip())
                st.session_state.ticket_state = result
                if result.get("solution"):
                    st.session_state.stage = "solution"
                else:
                    st.session_state.stage = "pending"
            st.rerun()


# ─── STAGE 2: SOLUTION FOUND ──────────────────────────────────────

elif st.session_state.stage == "solution":
    ticket_state = st.session_state.ticket_state
    ticket_id = st.session_state.ticket_id

    st.success(f" Ticket #{ticket_id} — Solution Found")
    source = ticket_state.get("solution_source", "chromadb")
    if source == "chromadb":
        st.info(" This solution was found from our knowledge base.")
    else:
        st.info("This solution was provided by our IT team.")

    st.subheader("Suggested Solution")
    st.write(ticket_state.get("solution"))
    st.divider()
    st.subheader("Did this solution work for you?")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Yes, it worked!", type="primary", use_container_width=True):
            with st.spinner("Closing your ticket..."):
                set_user_feedback(ticket_id, "worked")
                st.session_state.stage = "resolved"
            st.rerun()

    with col2:
        if st.button(" No, it didn't work", use_container_width=True):
            with st.spinner("Forwarding to IT team..."):
                set_user_feedback(ticket_id, "not_worked")
                member = get_least_busy_member()
                assign_ticket(ticket_id, member["member_id"])
                increment_workload(member["member_id"])
                st.session_state.ticket_state = {
                    **st.session_state.ticket_state,
                    "assigned_name": member["name"],
                    "status": "pending_it"
                }
                st.session_state.stage = "pending"
            st.rerun()


# ─── STAGE 3: PENDING IT ──────────────────────────────────────────

elif st.session_state.stage == "pending":
    ticket_id = st.session_state.ticket_id
    ticket_state = st.session_state.ticket_state
    assigned_name = ticket_state.get("assigned_name", "an IT member")

    st.warning(f"⏳ Ticket #{ticket_id} — Awaiting IT Support")
    st.write(f"Your ticket has been assigned to **{assigned_name}**.")
    st.write("Please wait while they work on your issue. Refresh to check for updates.")
    st.divider()

    if st.button("🔄 Check for updates", use_container_width=True):
        with st.spinner("Checking ticket status..."):
            ticket = get_ticket(ticket_id)
            if ticket and ticket.get("status") == "resolved":
                st.session_state.ticket_state = {
                    **st.session_state.ticket_state,
                    "solution": ticket.get("solution"),
                    "solution_source": "it_member"
                }
                st.session_state.stage = "solution"
                st.rerun()
            else:
                st.info("Your ticket is still being worked on. Please check back later.")


# ─── STAGE 4: RESOLVED ────────────────────────────────────────────

elif st.session_state.stage == "resolved":
    ticket_id = st.session_state.ticket_id
    st.balloons()
    st.success(f" Ticket #{ticket_id} — Resolved!")
    st.write("Your issue has been resolved and the ticket is now closed.")
    st.write("The solution has been saved to our knowledge base for future reference.")
    st.divider()
    if st.button("➕ Raise a new ticket", use_container_width=True):
        st.session_state.ticket_id = None
        st.session_state.ticket_state = None
        st.session_state.stage = "input"
        st.rerun()
