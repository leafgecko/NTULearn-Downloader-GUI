# NTULearn-Downloader-GUI

GUI wrapper around the [ntu_learn_downloader](https://github.com/leafgecko/ntulearn_downloader)

# Development Set up

We recommend to using [virtual environments](https://docs.python.org/3/tutorial/venv.html) when developing:

```
python3 -m venv venv
# on Mac/Linux
source venv/bin/activate
# on Windows
call venv\scripts\activate.bat
```

Install dependancies:

```
pip install deps/ntu_learn_downloader-0.2.1.tar.gz
# on Mac/Linux
pip install -r requirements.txt
# on windows
pip install -r requirements_windows.txt
```

To run tests:
```
cd src/main/python
nosetests --nocapture
```

# Running/Compilation

To run the app in GUI mode:
```sh
fbs run
```

To compile into a standalone executable:
```sh
fbs freeze
```

To create an installer (platform specific)
```
fbs installer
```
