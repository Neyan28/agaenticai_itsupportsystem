from typing import TypedDict, Optional


class TicketState(TypedDict):
    ticket_id: int
    user_query: str
    solution: Optional[str]
    solution_source: Optional[str]
    assigned_to: Optional[int]
    assigned_name: Optional[str]
    status: str
    user_feedback: Optional[str]
