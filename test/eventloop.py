import asyncio

async def slow_operation(future):
    future.set_result('Future is done!')

loop = asyncio.get_event_loop()
future1 = asyncio.Future()

asyncio.ensure_future(slow_operation(future1))

loop.run_until_complete(future1)
loop.close()
print(future1.result())

# loop.close()
