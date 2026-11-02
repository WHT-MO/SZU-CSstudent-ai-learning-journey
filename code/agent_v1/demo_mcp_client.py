from mcp import Client, StdioServerParameters
import asyncio
import sys
from pathlib import Path
from functools import partial

from mcp_adapter import convert_mcp_tools, build_mcp_functions
from agent_runner import run_agent

async def main():
    server_path = Path(__file__).resolve().parent / "demo_mcp_server.py"

    server_params = StdioServerParameters( #参数
        command=sys.executable,
        args=[str(server_path)],
    )

    async with Client(server_params) as client:
        tool_result = await client.list_tools()
        agent_tools = convert_mcp_tools(tool_result.tools) #MCP工具参数本地化

        for tool in agent_tools:
            print(tool.name)
            print(tool.description)
            print(tool.parameters)

        mcp_functions = build_mcp_functions(client, agent_tools) 
        agent_result = await run_agent(
            "请调用 get_python_version，告诉我工具服务进程的 Python 版本。",
            session_id="mcp_demo",
            mcp_tools=agent_tools,
            mcp_functions=mcp_functions,
        )
        
        if agent_result["completed"] == True:
            print(agent_result["message"]["content"])
        else:
            print(agent_result["reason"])

if __name__ == "__main__":
    asyncio.run(main())