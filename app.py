import os
from wsgiref import headers
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from pypdf import PdfReader
from dotenv import load_dotenv
import requests
import json
from reportlab.pdfgen import canvas
from io import BytesIO

# Load Environment Variables
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


print(
    "OpenRouter Key Loaded:",
    OPENROUTER_API_KEY[:10] if OPENROUTER_API_KEY else "NOT FOUND"
)

# Flask App
app = Flask(__name__)

app.config["SECRET_KEY"] = "resumeanalyzer123"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

latest_result = ""


# ---------------- USER MODEL ---------------- #

class User(UserMixin, db.Model):

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(100), unique=True, nullable=False)

    password = db.Column(db.String(255), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------------- SIGNUP ---------------- #

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        username = request.form["username"]

        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user:

            flash("Username already exists.")

            return redirect(url_for("signup"))

        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        new_user = User(
            username=username,
            password=hashed_password
        )

        db.session.add(new_user)

        db.session.commit()

        flash("Account created successfully.")

        return redirect(url_for("login"))

    return render_template("signup.html")


# ---------------- LOGIN ---------------- #

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]

        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password, password):

            login_user(user)

            return redirect(url_for("home"))        
        flash("Invalid Username or Password")

    return render_template("login.html")


# ---------------- LOGOUT ---------------- #

@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect(url_for("login"))

# ---------------- HOME ---------------- #

@app.route("/")
@login_required
def home():

    return render_template("index.html")


# ---------------- UPLOAD ---------------- #

@app.route("/upload", methods=["POST"])
@login_required
def upload():

    global latest_result

    if "resume" not in request.files:
        return "No file uploaded."

    file = request.files["resume"]

    job_description = request.form.get("jobDescription")

    action = request.form.get("action")

    if file.filename == "":
        return "Please select a PDF."

    upload_folder = "uploads"

    os.makedirs(upload_folder, exist_ok=True)

    file_path = os.path.join(upload_folder, file.filename)

    file.save(file_path)

    reader = PdfReader(file_path)

    resume_text = ""

    for page in reader.pages:

        text = page.extract_text()

        if text:

            resume_text += text


    # -------- COVER LETTER -------- #

    if action == "cover":

        prompt = f"""
You are a professional HR recruiter.

Write a professional Cover Letter.

Resume:

{resume_text}

Job Description:

{job_description}

Write:

1. Greeting

2. Introduction

3. Skills

4. Why I am suitable

5. Closing

Professional format.
"""

    # -------- ATS ANALYSIS -------- #

    else:

        prompt = f"""
You are an AI ATS Resume Analyzer.

Compare Resume and Job Description.

Resume:

{resume_text}

Job Description:

{job_description}

Provide:

1. ATS Score

2. Job Match Percentage

3. Matching Skills

4. Missing Skills

5. Resume Summary

6. Strengths

7. Weaknesses

8. Suggestions

9. 10 Interview Questions

Professional format.
"""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "openai/gpt-4.1-mini",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 1000
    }

    print("API KEY:", OPENROUTER_API_KEY)
    print("HEADERS:", headers)


    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=data
    )

    result = response.json()

    print(result)

    if "choices" not in result:
        return f"OpenRouter Error: {result}"

    latest_result = result["choices"][0]["message"]["content"]

    return render_template(
        "result.html",
        result=latest_result
    )
@app.route("/download")
@login_required
def download_pdf():

    global latest_result

    buffer = BytesIO()

    pdf = canvas.Canvas(buffer)

    pdf.setFont("Helvetica", 12)

    y = 800

    for line in latest_result.split("\n"):

        pdf.drawString(40, y, line[:100])

        y -= 18

        if y < 40:

            pdf.showPage()

            pdf.setFont("Helvetica", 12)

            y = 800

    pdf.save()

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="AI_Resume_Report.pdf",
        mimetype="application/pdf"
    )


# ---------------- DATABASE ---------------- #

with app.app_context():

    db.create_all()


# ---------------- RUN APP ---------------- #

if __name__ == "__main__":

    app.run(debug=True)