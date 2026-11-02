from mcp.server import MCPServer
import sys

server = MCPServer("course-tools")

@server.tool()
def get_python_version() -> str:
    """返回工具服务所在进程的Python版本"""
    return sys.version


if __name__ == "__main__":
    server.run(transport="stdio")