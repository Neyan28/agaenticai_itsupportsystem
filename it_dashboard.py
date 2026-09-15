import streamlit as st
import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db.postgres import get_all_members, get_tickets_for_member
from agent.graph import resume_ticket

load_dotenv()

st.set_page_config(page_title="IT Staff Dashboard", page_icon="🛠️", layout="centered")
st.title("🛠️ IT Staff Dashboard")
st.caption("View and resolve tickets assigned to you.")

if "resolved_tickets" not in st.session_state:
    st.session_state.resolved_tickets = []

st.subheader("Who are you?")
members = get_all_members()
member_names = [m["name"] for m in members]
member_map = {m["name"]: m for m in members}

selected_name = st.selectbox("Select your name", options=["-- Select --"] + member_names)

if selected_name == "-- Select --":
    st.info("Please select your name to view your assigned tickets.")
    st.stop()

selected_member = member_map[selected_name]
st.divider()

col1, col2 = st.columns(2)
with col1:
    st.metric(label="Your Active Tickets", value=selected_member["active_tickets"])
with col2:
    st.metric(label="Member ID", value=selected_member["member_id"])

st.divider()
st.subheader(f"Tickets assigned to {selected_name}")

if st.button("🔄 Refresh tickets", use_container_width=True):
    st.rerun()

tickets = get_tickets_for_member(selected_member["member_id"])

if not tickets:
    st.success("✅ No pending tickets. You are all caught up!")
else:
    st.write(f"You have **{len(tickets)}** pending ticket(s).")
    st.divider()

    for ticket in tickets:
        ticket_id = ticket["ticket_id"]

        if ticket_id in st.session_state.resolved_tickets:
            continue

        with st.container():
            st.markdown(f"### 🎫 Ticket #{ticket_id}")
            col1, col2 = st.columns([2, 1])
            with col1:
                st.write("**User problem:**")
                st.info(ticket["user_query"])
            with col2:
                st.write("**Raised at:**")
                st.write(str(ticket["created_at"]).split(".")[0])

            solution_text = st.text_area(
                "Your solution",
                key=f"solution_{ticket_id}",
                placeholder="Type your solution here...",
                height=120
            )

            col_submit, col_skip = st.columns(2)
            with col_submit:
                if st.button("✅ Submit Solution", key=f"submit_{ticket_id}", type="primary", use_container_width=True):
                    if not solution_text.strip():
                        st.warning("Please type a solution before submitting.")
                    else:
                        with st.spinner(f"Resolving ticket #{ticket_id}..."):
                            try:
                                resume_ticket(ticket_id, solution_text.strip())
                                st.session_state.resolved_tickets.append(ticket_id)
                                st.success(f"✅ Ticket #{ticket_id} resolved successfully!")
                            except Exception as e:
                                st.error(f"Error resolving ticket: {str(e)}")
                        st.rerun()

            with col_skip:
                if st.button("⏭️ Skip for now", key=f"skip_{ticket_id}", use_container_width=True):
                    st.info(f"Ticket #{ticket_id} skipped.")

            st.divider()

st.caption("Powered by LangGraph + OpenAI + ChromaDB + PostgreSQL")
