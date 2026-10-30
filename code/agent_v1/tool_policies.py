def read_only_guard(tool_name, validated_args) -> str | None: #只读权限
    if tool_name in {"read_file", "list_files", "search_file"}:
        return None
    
    return f"只读模式，拒绝执行：{tool_name}"