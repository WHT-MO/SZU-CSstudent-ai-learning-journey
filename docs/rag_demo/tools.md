# 文件工具与只读策略

文件工具的path相对于code/agent_v1/workspace/。
read_file读取指定文件，可按从1开始的行号选择范围，包含起止行。
search_file在单个文件内按字面、区分大小写搜索，并返回匹配行号。
只读策略允许read_file、list_files和search_file。
只读策略拒绝write_file、edit_file和run_python，因此不能修改文件或执行脚本。
只读策略在工具执行前检查工具名；被拒绝的请求以工具结果返回原因。
