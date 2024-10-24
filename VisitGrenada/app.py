from flask import Flask, render_template, url_for

app = Flask(__name__)

@app.route("/")
def homepage():
    return render_template('index.html')

@app.route("/visit")
def visit():
    return render_template('visitinfo.html')

@app.route("/oceanlife")
def oceanlife():
    return render_template('oceanlife.html')

@app.route("/carnival")
def carnival():
    return render_template('carnival.html')

@app.route("/spiceandfood")
def spiceandfood():
    return render_template('spiceandfood.html')

@app.route("/caribbean")
def caribbean():
    return render_template('caribbean.html')

@app.route("/activities")
def activities():
    return render_template('activities.html')

@app.route("/aboutus")
def aboutus():
    return render_template('aboutus.html')

if __name__ == "__main__":
    app.run()