from flask import Flask

app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello, World!"

app.run()

(a, b.c, d[e]) = 1, 2, 3
