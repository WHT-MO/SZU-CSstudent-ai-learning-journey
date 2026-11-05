from math import sqrt
from fastembed import TextEmbedding
import asyncio
import httpx

from tools import resolve_workspace_path
from model_client import non_stream_message

def load_knowledge_documents() -> list[dict]: #加载资料
    knowledge = resolve_workspace_path("knowledge")
    result = []

    for file_path in knowledge.glob("*.md"):
        file_content = file_path.read_text(encoding="utf-8")
        parts = {
            "path": f"knowledge/{file_path.name}", "content": file_content,
        }
        result.append(parts)

    return result

def retrieve_knowledge(documents: list[dict], keywords: list[str]) -> list[dict]: #关键词检索
    pass

def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float: #比较向量余弦相似度
    if len(vec_a) != len(vec_b):
        raise ValueError("向量维度不同")

    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = sqrt(sum(a ** 2 for a in vec_a))
    norm_b = sqrt(sum(b ** 2 for b in vec_b))

    if norm_a == 0 or norm_b == 0:
        raise ValueError("分母不能为零")
    return dot_product / (norm_a * norm_b)

async def main():
    embedding_model = TextEmbedding( #创建模型实例
        model_name="BAAI/bge-small-zh-v1.5",
        cache_dir=str(resolve_workspace_path(".models/fastembed")),
    )

    documents = load_knowledge_documents() #编码资料
    texts = [document["content"] for document in documents]
    documents_vectors = [ #模型生成向量
        vector.tolist() #数组转换成python列表
        for vector in embedding_model.passage_embed(texts)
    ]

    question = "会话study保存在哪里？只读模式能否修改文件和运行脚本？" #编码问题
    question_vector = list(embedding_model.query_embed(question))[0].tolist()

    scored_documents = [] #配对向量
    for document, vector in zip(documents, documents_vectors):
        sim = cosine_similarity(question_vector, vector)
        scored_documents.append({"document": document, "score": sim})
        print(document["path"], sim)

    selected_results = sorted(scored_documents, key=lambda scored_documents: scored_documents["score"], reverse=True)[:2] #取top_2资料
    context_parts = [
        f"来源：{selected_result["document"]["path"]} \n资料正文：{selected_result["document"]["content"]}"
        for selected_result in selected_results
    ]
    context = "\n\n".join(context_parts)

    messages = [
        {
            "role": "system",
            "content": "依据提供的资料回答，资料不足时说明不足，并标注来源路径",
        },
        {
            "role": "user",
            "content": f"问题：{question} \n{context}"
        },
    ]
    async with httpx.AsyncClient(timeout=60) as client:
        reply = await non_stream_message(client, messages, tools=[])

        if reply is None:
            print("回答生成失败")
            return

        print(reply["content"])

if __name__ == "__main__":
    asyncio.run(main())