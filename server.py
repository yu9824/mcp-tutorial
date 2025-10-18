"""
FastMCP quickstart example.

cd to the `examples/snippets/clients` directory and run:
    uv run server fastmcp_quickstart stdio
"""

import argparse
import logging

from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("Demo")


# Add an addition tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


# Add a dynamic greeting resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"


# Add a prompt
@mcp.prompt()
def greet_user(name: str, style: str = "friendly") -> str:
    """Generate a greeting prompt"""
    styles = {
        "friendly": "Please write a warm, friendly greeting",
        "formal": "Please write a formal, professional greeting",
        "casual": "Please write a casual, relaxed greeting",
    }

    return f"{styles.get(style, styles['friendly'])} for someone named {name}."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the FastMCP demo server")
    parser.add_argument(
        "--transport",
        default="stdio",
        help="Transport to use for MCP (default: stdio)",
    )
    # keep host/port optional for transports that may need them
    parser.add_argument(
        "--host", default=None, help="Host to bind (if applicable)"
    )
    parser.add_argument(
        "--port", type=int, default=None, help="Port to bind (if applicable)"
    )
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # configure basic logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logging.info(
        "Starting MCP server (transport=%s, host=%s, port=%s)",
        args.transport,
        args.host,
        args.port,
    )

    # Call run with available args; only pass host/port if provided
    run_kwargs = {"transport": args.transport}
    if args.host is not None:
        run_kwargs["host"] = args.host
    if args.port is not None:
        run_kwargs["port"] = args.port

    mcp.run(**run_kwargs)
