class Test:
    def __init__(self):
        pass

    def greeting(self, *args):
        print('hello world')


app = Test()

getattr(app, 'greeting')(None)

info = [{'name': 'hello'},{'name':'good'}]

more = {'gender': 'male'}

print(info)
