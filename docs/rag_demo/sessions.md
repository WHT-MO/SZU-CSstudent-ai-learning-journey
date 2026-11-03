# 会话存储约定

默认会话ID是default，存档位于code/agent_v1/session.json。
具名会话存档位于code/agent_v1/sessions/session_<session_id>.json。
例如会话study的存档是code/agent_v1/sessions/session_study.json。
会话ID允许英文字母、数字、下划线和连字符。
切换会话会让下一次任务使用选定会话的历史。
会话存档同时保存原始消息messages与摘要缓存summary_cache。
