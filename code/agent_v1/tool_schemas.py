from pydantic import BaseModel, Field
#--------------------参数模型-----------------------------------------------------
class AgentTool(BaseModel): #工具参数
    name: str
    description: str
    parameters: dict

class ReadFileArgs(BaseModel): #read参数
    path: str = Field(description="相对于workspace/的文件路径")
    start_line: int = Field(default=1, ge=1, description="从哪一行开始")
    end_line: int | None = Field(default=None, ge=1, description="在哪一行结束，省略或传null时读到文件末尾")

class WriteFileArgs(BaseModel): #write参数
    path: str = Field(description="相对于workspace/的文件路径")
    content: str = Field(description="要写入文件的文本")

class ListFilesArgs(BaseModel): #list参数
    path: str = Field(description="相对于workspace/的目录路径")

class EditFileArgs(BaseModel): #edit参数
    path: str = Field(description="相对于workspace/的文件路径")
    old_text: str = Field(description="要修改的旧文本")
    new_text: str = Field(description="要替换的新文本")

class SearchFileArgs(BaseModel): #search参数
    path: str = Field(description="相对于workspace/的文件路径")
    query: str = Field(min_length=1, description="待搜索文字,按原样匹配，区分大小写")
    max_matches: int = Field(default=20, ge=1, le=100, description="最多返回的匹配行数")

class RunPythonArgs(BaseModel): #runpython参数
    path: str = Field(description="相对于workspace/的文件路径")
#--------------------工具说明书----------------------------------------------------
read_file_tool = AgentTool( #read工具说明
    name="read_file",
    description="读取workspace/下的文件，行号从1开始，包含起始行和结束行",
    parameters=ReadFileArgs.model_json_schema()
    )
write_file_tool = AgentTool( #write工具说明
    name="write_file",
    description="写入保存的文本内容",
    parameters=WriteFileArgs.model_json_schema()
    )
list_files_tool = AgentTool( #list工具说明
    name="list_files",
    description="列出目录下文件名",
    parameters=ListFilesArgs.model_json_schema()
    )
edit_file_tool = AgentTool( #edit工具说明
    name="edit_file",
    description="替换一段文本",
    parameters=EditFileArgs.model_json_schema()
    )
search_file_tool = AgentTool(
    name="search_file",
    description="在单个文件中搜索文字，区分大小写，返回从1开始的行号，并限制匹配行数",
    parameters=SearchFileArgs.model_json_schema()
)
run_python_tool = AgentTool(
    name="run_python",
    description="运行Python脚本",
    parameters=RunPythonArgs.model_json_schema()
)
#--------------------注册表------------------------------------------------------
tool_arg_models = { #已注册工具
    "read_file": ReadFileArgs,
    "write_file": WriteFileArgs,
    "list_files": ListFilesArgs,
    "edit_file": EditFileArgs,
    "search_file": SearchFileArgs,
    "run_python": RunPythonArgs,
}

tool_specs = [ #模型工具列表
    read_file_tool,
    write_file_tool,
    list_files_tool,
    edit_file_tool,
    search_file_tool,
    run_python_tool,
]
