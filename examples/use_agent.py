"""
Example: Using DeepMCP with a custom model over HTTP.

Now with fancy console output:
- Shows discovered tools
- Shows each tool call + result
- Shows final LLM answer
"""

import asyncio
from dotenv import load_dotenv
from deepmcpagent import HTTPServerSpec, build_deep_agent
from langchain_openai import ChatOpenAI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from langchain.chat_models import init_chat_model

from deepmcpagent.prompt import UNIVERSAL_SYSTEM_PROMPT

async def main() -> None:
    console = Console()
    load_dotenv()

    servers = {
        "math": HTTPServerSpec(
            url="http://127.0.0.1:8000/mcp/math",
            transport="http",
        ),
        "sql": HTTPServerSpec(
            url="http://127.0.0.1:8001/mcp/sql",
            transport="http",
        ),
    }

    model = init_chat_model(
        "llama3.1:8b",           # kein -instruct nötig
        model_provider="ollama",
        config={
            "base_url": "http://127.0.0.1:11434",
            "temperature": 0.2,
        },
    )


    graph, loader = await build_deep_agent(
       servers=servers,
       model=model,
       instructions=UNIVERSAL_SYSTEM_PROMPT,
    )
    
    try:
        all_infos = await loader.list_tool_info()
        table = Table(title="Discovered MCP Tools", show_lines=True)
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Description", style="green")
        
        forbidden = {"task", "plan", "subagent"}
        
        for t in all_infos:
            table.add_row(t.name, t.description or "-")
        console.print(table)
        
        if any(t.name in forbidden for t in all_infos):
            tools = [t for t in await loader.get_tools() if t.name not in forbidden]
            from langgraph.prebuilt import create_react_agent
            graph = create_react_agent(model=model, tools=tools, state_modifier=UNIVERSAL_SYSTEM_PROMPT)
    except Exception:
        pass

    query = (
        "Give me a high-level overview of the database contents. "
        "List a few tables from the main schema and preview 5 rows from 1-2 relevant tables."
    )
    console.print(Panel.fit(query, title="User Query", style="bold magenta"))

    result = await graph.ainvoke({
        "messages": [{"role": "user", "content": query}]
    })

    # Iterate messages for tool calls and outputs
    console.print("\n[bold yellow]Agent Trace:[/bold yellow]")
    for msg in result["messages"]:
        role = msg.__class__.__name__
        if role == "AIMessage" and msg.tool_calls:
            for call in msg.tool_calls:
                console.print(f"[cyan]→ Invoking tool:[/cyan] [bold]{call['name']}[/bold] with {call['args']}")
        elif role == "ToolMessage":
            console.print(f"[green]✔ Tool result from {msg.name}:[/green] {msg.content}")
        elif role == "AIMessage" and msg.content:
            console.print(Panel(msg.content, title="Final LLM Answer", style="bold green"))


if __name__ == "__main__":
    asyncio.run(main())
