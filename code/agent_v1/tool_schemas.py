from pydantic import BaseModel, Field


class AgentTool(BaseModel):
    name: str
    description: str
    parameters: dict


class ReadFileArgs(BaseModel):
    path: str = Field(description="相对于workspace/的文件路径")


class WriteFileArgs(BaseModel):
    path: str = Field(description="相对于workspace/的文件路径")
    content: str = Field(description="要写入文件的文本")


class ListFilesArgs(BaseModel):
    path: str = Field(description="相对于workspace/的目录路径")


class EditFileArgs(BaseModel):
    path: str = Field(description="相对于workspace/的文件路径")
    old_text: str = Field(description="要修改的旧文本")
    new_text: str = Field(description="用于替换旧文本的新文本")

read_file_tool = AgentTool(
    name="read_file",
    description="读取workspace/下的文件",
    parameters=ReadFileArgs.model_json_schema(),
)
write_file_tool = AgentTool(
    name="write_file",
    description="将文本写入workspace/下的文件",
    parameters=WriteFileArgs.model_json_schema(),
)
list_files_tool = AgentTool(
    name="list_files",
    description="列出workspace/下指定目录的文件名",
    parameters=ListFilesArgs.model_json_schema(),
)
edit_file_tool = AgentTool(
    name="edit_file",
    description="替换workspace/下指定文件中的一段文本",
    parameters=EditFileArgs.model_json_schema(),
)


if __name__ == "__main__":
    for tool in (read_file_tool, write_file_tool, list_files_tool, edit_file_tool):
        print(tool.name, tool.parameters)
