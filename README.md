# Daniel Stelzer's Cuneiform Tools

This repository holds all the code related to the kadaru encoding, as presented in my PhD thesis and various other publications. The organization is rather a mess, but I'll be working on that when I have some time.

For now:
- `/hantatallas/` contains all the basic kadaru algorithms
- `/sanhatallas/` contains the drawn stroke recognition algorithms
- `/flask_main.py`, `/templates/`, and `/*.html` contain the web app running at https://dstelzer.pythonanywhere.com
- `/*.py` are other experiments unrelated to the kadaru encoding, like the program that generates line drawings for demonstrating Sanhatallas

Look in `/hantatallas/` first; that's where most of the important stuff is. Most of the Python files in that directory can be run as standalone programs to test their features; for those that can't, `/hantatallas/main.py` shows how to invoke them.

Have fun!
