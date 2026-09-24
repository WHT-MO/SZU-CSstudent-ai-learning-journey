import asyncio

async def show_state(current_state):
    print(len(current_state["messages"]))
    print(current_state)

async def record_state(current_state):
    event_log.append(len(current_state["messages"]))

async def emit(message):
    state["messages"].append(message)
    for listener in listeners:
        await listener(state)

async def task():
    await emit("hello")
    print(event_log)
    await emit("two")
    print(event_log)

state = {"messages":[]}
event_log = []
listeners = [show_state,record_state]

asyncio.run(task())