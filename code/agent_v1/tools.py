from pathlib import Path

from tool_schemas import (
    EditFileArgs,
    ListFilesArgs,
    ReadFileArgs,
    WriteFileArgs,
)


workspace_root = Path(__file__).resolve().parent / "workspace"


def resolve_workspace_path(relative_path: str) -> Path:
    """把 workspace 相对路径转换成安全的绝对路径。"""
    workspace_path = workspace_root.resolve()
    candidate_path = (workspace_path / relative_path).resolve()

    try:
        candidate_path.relative_to(workspace_path)
    except ValueError as error:
        raise ValueError("路径超出 workspace") from error

    return candidate_path


def read_file(file_args: ReadFileArgs) -> str:
    file_path = resolve_workspace_path(file_args.path)
    return file_path.read_text(encoding="utf-8")


def write_file(file_args: WriteFileArgs) -> str:
    file_path = resolve_workspace_path(file_args.path)
    file_path.write_text(file_args.content, encoding="utf-8")
    return f"文件已写入：{file_args.path}"


def list_files(file_args: ListFilesArgs) -> str:
    directory_path = resolve_workspace_path(file_args.path)

    if not directory_path.is_dir():
        raise NotADirectoryError(f"不是目录：{file_args.path}")

    file_names = sorted(item.name for item in directory_path.iterdir())

    if not file_names:
        return "目录为空"

    return "\n".join(file_names)


def edit_file(file_args: EditFileArgs) -> str:
    if not file_args.old_text:
        raise ValueError("old_text 不能为空")

    file_path = resolve_workspace_path(file_args.path)
    content = file_path.read_text(encoding="utf-8")
    match_count = content.count(file_args.old_text)

    if match_count == 0:
        raise ValueError("没有找到要替换的旧文本")

    if match_count > 1:
        raise ValueError("旧文本出现多次，无法确定替换位置")

    updated_content = content.replace(file_args.old_text, file_args.new_text, 1)
    file_path.write_text(updated_content, encoding="utf-8")
    return f"文件已修改：{file_args.path}"


tool_functions = {
    "read_file": read_file,
    "write_file": write_file,
    "list_files": list_files,
    "edit_file": edit_file,
}
