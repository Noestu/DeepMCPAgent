from __future__ import annotations
from fastmcp import FastMCP

mcp = FastMCP("Math")

@mcp.tool(
    name="add",
    description=(
        "Add two integers together. "
        "Both inputs must be plain integers, not expressions. "
    )
)
def add(a: int, b: int) -> int:
    """Add two integers and return the sum."""
    return a + b


@mcp.tool(
    name="multiply",
    description=(
        "Multiply two integers together. "
        "Both inputs must be plain integers, not expressions. "
        "If you need to multiply the result of an addition, "
        "first call 'add', then pass the integer result here. "
    )
)
def multiply(a: int, b: int) -> int:
    """Multiply two integers and return the product."""
    return a * b


if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="127.0.0.1",
        port=8000,
        path="/mcp/math"
    )
