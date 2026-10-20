import asyncio

note = {"content": "旧内容"}

async def write_note():
    await asyncio.sleep(1)
    note["content"] = "新内容"
    print("写入完成")
    return "写入完成"

async def read_note():
    print(note["content"])
    return note["content"]

async def main():
    note["content"] = "旧内容"
    await asyncio.gather(write_note(), read_note())

    note["content"] = "旧内容"
    await write_note()
    await read_note()

if __name__ == "__main__":
    asyncio.run(main())