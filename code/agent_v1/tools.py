from pathlib import Path
import subprocess
import sys

from tool_schemas import (
    EditFileArgs,
    ListFilesArgs,
    ReadFileArgs,
    WriteFileArgs,
    SearchFileArgs,
    RunPythonArgs,
)


workspace_root = Path(__file__).resolve().parent / "workspace" #设置工作区

#路径安全检查
def resolve_workspace_path(relative_path: str) -> Path:
    """把 workspace 相对路径转换成安全的绝对路径。"""
    workspace_path = workspace_root.resolve()
    candidate_path = (workspace_path / relative_path).resolve()

    try:
        candidate_path.relative_to(workspace_path)
    except ValueError as error:
        raise ValueError("路径超出 workspace") from error

    return candidate_path

#read工具
def read_file(file_args: ReadFileArgs) -> str:
    if file_args.end_line and file_args.end_line < file_args.start_line:
        raise ValueError("结束行不能小于起始行")
    
    file_path = resolve_workspace_path(file_args.path)
    lines = file_path.read_text(encoding="utf-8").splitlines(keepends=True)
    total_lines = len(lines)
    selected = lines[file_args.start_line - 1:file_args.end_line]

    if not lines:
        return "文件为空"

    if total_lines < file_args.start_line:
        raise ValueError(f"文件共{total_lines}行")

    actual_end = file_args.start_line + len(selected) - 1

    return f"【{file_args.path}: 第{file_args.start_line}-{actual_end}行，共{total_lines}行】\n" + "".join(selected)

#write工具
def write_file(file_args: WriteFileArgs) -> str:
    file_path = resolve_workspace_path(file_args.path)
    file_path.write_text(file_args.content, encoding="utf-8")
    return f"文件已写入：{file_args.path}"

#list工具
def list_files(file_args: ListFilesArgs) -> str:
    directory_path = resolve_workspace_path(file_args.path)

    if not directory_path.is_dir():
        raise NotADirectoryError(f"不是目录：{file_args.path}")

    file_names = sorted(item.name for item in directory_path.iterdir())

    if not file_names:
        return "目录为空"

    return "\n".join(file_names)

#edit工具
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

#search工具
def search_file(file_args: SearchFileArgs) -> str:
    file_path = resolve_workspace_path(file_args.path)
    lines = file_path.read_text(encoding="utf-8").splitlines(keepends=True)
    selected = []

    for line_number, line in enumerate(lines, start=1):        
        if file_args.query in line:
            if len(selected) >= file_args.max_matches:
                selected.append("仍有匹配未展示")
                break
            else:
                selected.append(f"{file_args.path}:{line_number}:{line}")

    if not selected:
        return "没有匹配结果"
    return "".join(selected)

#runpython工具
def run_python(file_args: RunPythonArgs) -> str:
    script_path = resolve_workspace_path(file_args.path)
    try:
        result = subprocess.run( #返回退出码returncode、标准输出stdout、错误输出stderr
            args=[sys.executable, "-X", "utf8", str(script_path)], #固定解释器和编码
            cwd=workspace_root, #相对路径起点
            capture_output=True, #收集stdout、stderr
            text=True, #读取文字
            encoding="utf-8", #统一编码
            stdin=subprocess.DEVNULL, #无需终端输入
            timeout=5, #子进程运行等待
            check=False, #非0退出也返回结果对象
        )
    except subprocess.TimeoutExpired:
        raise TimeoutError
    
    return f"\n退出码：{result.returncode} \n标准输出：\n{result.stdout} \n错误输出：\n{result.stderr}"