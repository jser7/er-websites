from flask import Flask, render_template, url_for

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/projects')
def projects():
    return render_template('projects.html')

@app.route('/biography')
def biography():
    return render_template('biography.html')

if __name__ == "__main__":
    app.run()