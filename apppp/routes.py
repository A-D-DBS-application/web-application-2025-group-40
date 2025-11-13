from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def choose_role():
    return render_template('choose_role.html')  # je swipe-pagina

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')
