# python-openimu

## Install all dependencies
python 2.7
```
pip install -r requirements-2.x.txt
```

python 3
```
pip install -r requirements.txt
```

## Run from source code

### Compatible
The project references `tornado`, if you have installed python 3.8 on windows, there is some compatible code should be added. For more information, please take a look [here](https://www.tornadoweb.org/en/stable/index.html#installation). The compatible code should be added in webserver.py.

```
python ./webserver.py
```

## Pack to pip package
```
python ./setup.py sdist
```

## Build a executor
```
pyinstaller webserver.spec
```
