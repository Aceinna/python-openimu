import time
import asyncio
from asyncio import Queue


def now(): return time.time()


async def worker(q):  # 工作者消费队列
    print('Start worker')

    while 1:  # 无限循环
        start = now()
        task = await q.get()  # 开始消费
        if not task:
            await asyncio.sleep(1)
            continue
        print('working on ', int(task))
        await asyncio.sleep(int(task))
        q.task_done()  # 队列通知
        print('Job Done for ', task, now() - start)


async def generate_run(q):  # 生成worker线程函数
    asyncio.ensure_future(worker(q))
    asyncio.ensure_future(worker(q))  # 先弄了两个worker去跑
    await q.join()  # 主线程挂起等待队列完成通知
    jobs = asyncio.Task.all_tasks()  # 完成后收集所有线程，这里是3个，算上自己
    print('是否已经关闭任务', asyncio.gather(*jobs).cancel())  # 关闭线程方法，返回True


def main():

    loop = asyncio.get_event_loop()
    q = Queue()
    for i in range(3):
        q.put_nowait(str(i))  # 一定要放入字符，数字0是空，队列一直不会结束。
    loop.run_until_complete(generate_run(q))  # 启动生成函数

    loop.close()


if __name__ == '__main__':
    main()
