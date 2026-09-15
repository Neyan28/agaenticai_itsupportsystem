import json
import os
import sys
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.postgres import (
    get_ticket, update_ticket_status, assign_ticket,
    increment_workload, decrement_workload, get_least_busy_member,
    get_all_members, get_tickets_for_member, resolve_ticket
)

load_dotenv()

app = Server("postgres-mcp")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(name="get_least_busy_member", description="Find IT member with lowest active tickets.", inputSchema={"type": "object", "properties": {}, "required": []}),
        Tool(name="assign_ticket", description="Assign ticket to IT member.", inputSchema={"type": "object", "properties": {"ticket_id": {"type": "integer"}, "member_id": {"type": "integer"}}, "required": ["ticket_id", "member_id"]}),
        Tool(name="increment_workload", description="Increment IT member active ticket count.", inputSchema={"type": "object", "properties": {"member_id": {"type": "integer"}}, "required": ["member_id"]}),
        Tool(name="decrement_workload", description="Decrement IT member active ticket count.", inputSchema={"type": "object", "properties": {"member_id": {"type": "integer"}}, "required": ["member_id"]}),
        Tool(name="get_ticket", description="Fetch ticket details by ID.", inputSchema={"type": "object", "properties": {"ticket_id": {"type": "integer"}}, "required": ["ticket_id"]}),
        Tool(name="get_all_members", description="Fetch all IT members.", inputSchema={"type": "object", "properties": {}, "required": []}),
        Tool(name="get_tickets_for_member", description="Fetch pending tickets for a member.", inputSchema={"type": "object", "properties": {"member_id": {"type": "integer"}}, "required": ["member_id"]}),
        Tool(name="resolve_ticket", description="Mark ticket as resolved.", inputSchema={"type": "object", "properties": {"ticket_id": {"type": "integer"}, "solution": {"type": "string"}}, "required": ["ticket_id", "solution"]}),
        Tool(name="update_ticket_status", description="Update ticket status.", inputSchema={"type": "object", "properties": {"ticket_id": {"type": "integer"}, "status": {"type": "string"}}, "required": ["ticket_id", "status"]}),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "get_least_busy_member":
        return [TextContent(type="text", text=json.dumps(get_least_busy_member()))]
    elif name == "assign_ticket":
        assign_ticket(arguments["ticket_id"], arguments["member_id"])
        return [TextContent(type="text", text=json.dumps({"assigned": True}))]
    elif name == "increment_workload":
        increment_workload(arguments["member_id"])
        return [TextContent(type="text", text=json.dumps({"incremented": True}))]
    elif name == "decrement_workload":
        decrement_workload(arguments["member_id"])
        return [TextContent(type="text", text=json.dumps({"decremented": True}))]
    elif name == "get_ticket":
        return [TextContent(type="text", text=json.dumps(get_ticket(arguments["ticket_id"]), default=str))]
    elif name == "get_all_members":
        return [TextContent(type="text", text=json.dumps(get_all_members()))]
    elif name == "get_tickets_for_member":
        return [TextContent(type="text", text=json.dumps(get_tickets_for_member(arguments["member_id"]), default=str))]
    elif name == "resolve_ticket":
        resolve_ticket(arguments["ticket_id"], arguments["solution"])
        return [TextContent(type="text", text=json.dumps({"resolved": True}))]
    elif name == "update_ticket_status":
        update_ticket_status(arguments["ticket_id"], arguments["status"])
        return [TextContent(type="text", text=json.dumps({"updated": True}))]
    return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
