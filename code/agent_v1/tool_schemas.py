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