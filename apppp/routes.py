from flask import Flask, render_template

app = Flask(__name__)

@app.route('/choose_role')
def choose_role():
    return render_template('choose_role.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

if __name__ == "__main__":
    app.run(debug=True)
