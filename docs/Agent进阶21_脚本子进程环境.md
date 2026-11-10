# 进阶第21节 控制脚本继承的环境变量

`run_python()` 通过 `subprocess.run()` 启动另一个 Python 进程。`cwd` 指定脚本的起始工作目录。省略 `env` 时，子进程会继承 Agent 进程的环境变量，其中包括模型客户端用到的 `DEEPSEEK_API_KEY`（如果已配置）。[Python subprocess 文档](https://docs.python.org/3.12/library/subprocess.html#subprocess.run)

## 动手 从子进程的环境中移除模型密钥

在 `tools.py` 导入 `os`。在 `run_python()` 解析脚本路径后，用 `os.environ.copy()` 得到 `child_env`，再调用 `child_env.pop("DEEPSEEK_API_KEY", None)`。最后在现有的 `subprocess.run()` 中加入 `env=child_env`。

`copy()` 让你修改脚本即将收到的环境字典，Agent 自己还可以用原来的密钥发模型请求。`pop` 的第二个参数让未配置该键时也能启动脚本。复制后只移除这一个键，脚本仍能收到 `SystemRoot`、`PATH` 等正常配置。磁盘读写范围由子进程的系统权限决定。

2026-11-10，源码检查通过。`run_python()` 已将移除密钥后的环境副本传给 `subprocess.run()`。
