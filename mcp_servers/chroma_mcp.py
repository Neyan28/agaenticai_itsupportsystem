import os
import chromadb
from chromadb.utils import embedding_functions
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import json
from dotenv import load_dotenv

load_dotenv()

CHROMA_PERSIST_PATH = os.getenv("CHROMA_PERSIST_PATH", "./chroma_store")

chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_PATH)
embedding_fn = embedding_functions.DefaultEmbeddingFunction()
collection = chroma_client.get_or_create_collection(
    name="it_solutions",
    embedding_function=embedding_fn
)

app = Server("chroma-mcp")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="query_solution",
            description="Search ChromaDB for a semantically similar past solution.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_query": {"type": "string"},
                    "n_results": {"type": "integer", "default": 1}
                },
                "required": ["user_query"]
            }
        ),
        Tool(
            name="store_solution",
            description="Store a new IT solution into ChromaDB.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "integer"},
                    "user_query": {"type": "string"},
                    "solution": {"type": "string"}
                },
                "required": ["ticket_id", "user_query", "solution"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "query_solution":
        user_query = arguments["user_query"]
        n_results = arguments.get("n_results", 1)
        results = collection.query(query_texts=[user_query], n_results=n_results)

        if not results["documents"] or not results["documents"][0]:
            return [TextContent(type="text", text=json.dumps({"found": False, "solution": None}))]

        best_distance = results["distances"][0][0]
        best_solution = results["documents"][0][0]

        if best_distance > 0.3:
            return [TextContent(type="text", text=json.dumps({"found": False, "solution": None}))]

        return [TextContent(type="text", text=json.dumps({
            "found": True,
            "solution": best_solution,
            "distance": best_distance
        }))]

    elif name == "store_solution":
        collection.add(
            documents=[arguments["solution"]],
            metadatas=[{"ticket_id": str(arguments["ticket_id"]), "user_query": arguments["user_query"]}],
            ids=[f"ticket_{arguments['ticket_id']}"]
        )
        return [TextContent(type="text", text=json.dumps({"stored": True}))]

    return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
