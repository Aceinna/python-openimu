import datetime


class Test:
    def __init__(self):
        pass

    def greeting(self, *args):
        print('hello world')


app = Test()

getattr(app, 'greeting')(None)

info = [{'name': 'hello'}, {'name': 'good'}]

more = {'gender': 'male'}

print(info)
timeout = 1
input_result = None
start_time = datetime.datetime.now()
while input_result is None:
    end_time = datetime.datetime.now()
    span = end_time - start_time
    if span.total_seconds() > timeout:
        break
    print(start_time, end_time)
