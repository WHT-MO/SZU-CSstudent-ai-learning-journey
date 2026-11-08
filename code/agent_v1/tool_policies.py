READ_ONLY_TOOL_NAMES = {"read_file", "list_files", "search_file"}

def read_only_guard(tool_name, validated_args) -> str | None: #只读权限
    if tool_name in READ_ONLY_TOOL_NAMES:
        return None
    
    return f"只读模式，拒绝执行：{tool_name}"