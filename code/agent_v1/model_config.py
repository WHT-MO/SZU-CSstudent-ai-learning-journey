from pydantic import BaseModel

#模型配置参数
class ModelConfig(BaseModel):
    model: str
    max_output_tokens: int
    reasoning_effort: str = "high"

AGENT_MODEL_CONFIG = ModelConfig(
    model="deepseek-flash",
    max_output_tokens=20000,
    reasoning_effort="high",
)
SUMMARY_MODEL_CONFIG = ModelConfig(
    model="deepseek-flash",
    max_output_tokens=20000,
    reasoning_effort="low",
)