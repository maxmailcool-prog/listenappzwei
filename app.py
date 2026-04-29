import os
from datetime import datetime
from urllib.parse import urlparse

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

database_url = os.environ.get("DATABASE_URL", "sqlite:///shopping.db")
# Render/Heroku geben manchmal postgres:// aus, SQLAlchemy erwartet postgresql://
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(180), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    lists = db.relationship("ShoppingList", backref="user", lazy=True, cascade="all, delete-orphan")


class ShoppingList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    items = db.relationship("Item", backref="shopping_list", lazy=True, cascade="all, delete-orphan", order_by="Item.position")


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(300), nullable=False)
    checked = db.Column(db.Boolean, default=False)
    position = db.Column(db.Integer, default=0)
    list_id = db.Column(db.Integer, db.ForeignKey("shopping_list.id"), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


with app.app_context():
    db.create_all()


def get_user_list_or_404(list_id):
    return ShoppingList.query.filter_by(id=list_id, user_id=current_user.id).first_or_404()


@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Bitte E-Mail und Passwort eingeben.")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Das Passwort muss mindestens 6 Zeichen haben.")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("Diese E-Mail ist schon registriert.")
            return redirect(url_for("register"))

        user = User(email=email, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for("dashboard"))

    return render_template("auth.html", mode="register")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            flash("E-Mail oder Passwort ist falsch.")
            return redirect(url_for("login"))

        login_user(user, remember=True)
        return redirect(url_for("dashboard"))

    return render_template("auth.html", mode="login")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    lists = ShoppingList.query.filter_by(user_id=current_user.id).order_by(ShoppingList.updated_at.desc()).all()
    selected_id = request.args.get("list", type=int)
    current = None
    if selected_id:
        current = get_user_list_or_404(selected_id)
    elif lists:
        current = lists[0]
    return render_template("dashboard.html", lists=lists, current=current)


@app.route("/lists/new", methods=["POST"])
@login_required
def new_list():
    name = request.form.get("name", "").strip()
    if not name:
        name = "Neue Liste"

    shopping_list = ShoppingList(name=name, user_id=current_user.id)
    db.session.add(shopping_list)
    db.session.commit()
    return redirect(url_for("dashboard", list=shopping_list.id))


@app.route("/lists/<int:list_id>/save", methods=["POST"])
@login_required
def save_list(list_id):
    shopping_list = get_user_list_or_404(list_id)
    shopping_list.name = request.form.get("name", shopping_list.name).strip() or shopping_list.name

    texts = request.form.getlist("item_text")
    checked_ids = set(request.form.getlist("checked_id"))

    existing_items = {str(item.id): item for item in shopping_list.items}
    new_order = []

    pos = 0
    for item in list(shopping_list.items):
        text = request.form.get(f"text_{item.id}", "").strip()
        if text:
            item.text = text
            item.checked = str(item.id) in checked_ids
            item.position = pos
            new_order.append(item)
            pos += 1
        else:
            db.session.delete(item)

    new_items_raw = request.form.get("new_items", "")
    for line in new_items_raw.splitlines():
        line = line.strip()
        if line:
            db.session.add(Item(text=line, checked=False, position=pos, shopping_list=shopping_list))
            pos += 1

    shopping_list.updated_at = datetime.utcnow()
    db.session.commit()
    return redirect(url_for("dashboard", list=shopping_list.id))


@app.route("/lists/<int:list_id>/toggle/<int:item_id>", methods=["POST"])
@login_required
def toggle_item(list_id, item_id):
    shopping_list = get_user_list_or_404(list_id)
    item = Item.query.filter_by(id=item_id, list_id=shopping_list.id).first_or_404()
    item.checked = not item.checked
    shopping_list.updated_at = datetime.utcnow()
    db.session.commit()

    view = request.form.get("view", "dashboard")
    if view == "display":
        return redirect(url_for("display", list=list_id))
    return redirect(url_for("dashboard", list=list_id))


@app.route("/lists/<int:list_id>/delete", methods=["POST"])
@login_required
def delete_list(list_id):
    shopping_list = get_user_list_or_404(list_id)
    db.session.delete(shopping_list)
    db.session.commit()
    return redirect(url_for("dashboard"))


@app.route("/display")
@login_required
def display():
    lists = ShoppingList.query.filter_by(user_id=current_user.id).order_by(ShoppingList.updated_at.desc()).all()
    selected_id = request.args.get("list", type=int)
    current = None
    if selected_id:
        current = get_user_list_or_404(selected_id)
    elif lists:
        current = lists[0]
    return render_template("display.html", lists=lists, current=current)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)