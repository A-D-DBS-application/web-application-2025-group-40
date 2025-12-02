from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Group40Ufora%21@db.aicnouxwbuydippwukbs.supabase.co:5432/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# User model
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

# ------------------ ROUTES ------------------

@app.route('/choose_role')
def choose_role():
    return render_template('choose_role.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.form
        result = login_user(data['email'], data['password'])
        return jsonify(result)
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.form
        result = register_user(data['email'], data['password'])
        return jsonify(result)
    return render_template('register.html')

@app.route("/api/vacatures", methods=["GET"])
def get_vacatures():
    vacatures = [
        {"id": 1, "title": "Student Kassamedewerker", "description": "Weekendjob in supermarkt", "location": "Gent"},
        {"id": 2, "title": "IT Support Student", "description": "Helpdesk op campus", "location": "Antwerpen"},
        {"id": 3, "title": "Barista", "description": "Studentenjob in koffiebar", "location": "Leuven"}
    ]
    return jsonify(vacatures)

@app.route("/api/notificatie", methods=["POST"])
def send_notificatie():
    data = request.json
    vacature_id = data.get("vacatureId")
    print(f"Student heeft vacature {vacature_id} geliket!")
    return jsonify({"message": "Notificatie verzonden"}), 200

# ------------------ FUNCTIES ------------------

def register_user(email, password):
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return {"error": "Dit emailadres is al gebruikt."}

    new_user = User(email=email)
    new_user.set_password(password)

    try:
        db.session.add(new_user)
        db.session.commit()
        return {"success": "Account aangemaakt!"}
    except IntegrityError:
        db.session.rollback()
        return {"error": "Dit emailadres is al gebruikt."}

def login_user(email, password):
    user = User.query.filter_by(email=email).first()
    if not user:
        return {"error": "Geen account gevonden."}
    if not user.check_password(password):
        return {"error": "Verkeerd wachtwoord."}
    return {"success": "Ingelogd!"}

# ------------------ MAIN ------------------

if __name__ == "__main__":
    import sqlalchemy  # voeg dit hier bovenaan toe
    
    # Test Supabase verbinding
    try:
        engine = sqlalchemy.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
        with engine.connect() as conn:
            print("CONNECTED TO SUPABASE!")
    except Exception as e:
        print("FAILED:", e)

    db.create_all()  # maakt tabel aan als die nog niet bestaat
    app.run(debug=True)


if __name__ == "__main__":
    db.create_all()  # maakt de tabel aan als die nog niet bestaat
    app.run(debug=True)
