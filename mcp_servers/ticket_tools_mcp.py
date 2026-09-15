import json
import os
import sys
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.postgres import (
    get_least_busy_member, assign_ticket, increment_workload,
    decrement_workload, resolve_ticket, get_ticket
)

load_dotenv()

app = Server("ticket-tools-mcp")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(name="route_ticket", description="Route ticket to least busy IT member.", inputSchema={"type": "object", "properties": {"ticket_id": {"type": "integer"}}, "required": ["ticket_id"]}),
        Tool(name="close_ticket", description="Close resolved ticket and decrement workload.", inputSchema={"type": "object", "properties": {"ticket_id": {"type": "integer"}, "solution": {"type": "string"}}, "required": ["ticket_id", "solution"]}),
        Tool(name="get_ticket_status", description="Get current ticket status.", inputSchema={"type": "object", "properties": {"ticket_id": {"type": "integer"}}, "required": ["ticket_id"]}),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "route_ticket":
        member = get_least_busy_member()
        if not member:
            return [TextContent(type="text", text=json.dumps({"routed": False, "error": "No members available"}))]
        assign_ticket(arguments["ticket_id"], member["member_id"])
        increment_workload(member["member_id"])
        return [TextContent(type="text", text=json.dumps({
            "routed": True,
            "ticket_id": arguments["ticket_id"],
            "assigned_to": member["member_id"],
            "assigned_name": member["name"],
            "active_tickets": member["active_tickets"] + 1
        }))]

    elif name == "close_ticket":
        ticket = get_ticket(arguments["ticket_id"])
        if not ticket:
            return [TextContent(type="text", text=json.dumps({"closed": False, "error": "Ticket not found"}))]
        resolve_ticket(arguments["ticket_id"], arguments["solution"])
        if ticket.get("assigned_to"):
            decrement_workload(ticket["assigned_to"])
        return [TextContent(type="text", text=json.dumps({"closed": True}))]

    elif name == "get_ticket_status":
        ticket = get_ticket(arguments["ticket_id"])
        return [TextContent(type="text", text=json.dumps(ticket, default=str))]

    return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
