from tool_schemas import AgentTool
from tool_schemas import (
    ReadFileArgs,
    WriteFileArgs,
    ListFilesArgs,
    EditFileArgs,
    SearchFileArgs,
    RunPythonArgs,
)
from tools import (
    read_file,
    write_file,
    list_files,
    edit_file,
    search_file,
    run_python,
)

#注册表
tool_registry = {
    "read_file": {
        "args_model": ReadFileArgs,
        "function": read_file,
        "description": "读取工作区文件，支持指定行范围",
        "requires_serial": False,
    },
        "write_file": {
        "args_model": WriteFileArgs,
        "function": write_file,
        "description": "写入保存的文本内容",
        "requires_serial": True,
    },
        "list_files": {
        "args_model": ListFilesArgs,
        "function": list_files,
        "description": "列出目录下文件名",
        "requires_serial": False,
    },
        "edit_file": {
        "args_model": EditFileArgs,
        "function": edit_file,
        "description": "替换一段文本",
        "requires_serial": True,
    },
        "search_file": {
        "args_model": SearchFileArgs,
        "function": search_file,
        "description": "搜索文字，区分大小写，并限制匹配行数",
        "requires_serial": False,
    },
        "run_python": {
        "args_model": RunPythonArgs,
        "function": run_python,
        "description": "运行Python脚本",
        "requires_serial": True,
    },
}

tool_arg_models = {} #参数
tool_functions = {} #执行函数
tool_specs = [] #说明书
serial_tool_functions = [] #顺序执行策略

for name, info in tool_registry.items():
    tool_arg_models[name] = info["args_model"]

    tool_functions[name] = info["function"]

    spec = AgentTool(
        name=name,
        description=info["description"],
        parameters=info["args_model"].model_json_schema()
    )
    tool_specs.append(spec)
    
    if info["requires_serial"] is True:
        serial_tool_functions.append(info["function"])