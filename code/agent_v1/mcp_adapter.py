from tool_schemas import AgentTool
from functools import partial

def convert_mcp_tools(mcp_tools) -> list[AgentTool]: #转换工具参数
    agent_tools = []
    
    for tools in mcp_tools:
        agent_tool = AgentTool(
            name=tools.name,
            description=tools.description or "",
            parameters=tools.input_schema,
        )
        agent_tools.append(agent_tool)

    return agent_tools

def build_mcp_functions(client, agent_tools) -> dict: #转换传入参数
    mcp_functions = {}

    for tools in agent_tools:
        mcp_functions[tools.name] = partial(call_mcp_tool, client, tools.name)

    return mcp_functions

async def call_mcp_tool(client, tool_name: str, arguments: dict) -> str: #转换调用结果
    call_result = await client.call_tool(tool_name, arguments)
    parts = []

    for content in call_result.content:
        if content.type == "text":
            parts.append(content.text)

    tool_content = "\n".join(parts)
    if call_result.is_error == True:
        raise RuntimeError(tool_content)

    return tool_content

