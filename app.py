from flask import Flask, render_template, request, redirect, session, url_for
import time
import threading
import random



app = Flask(__name__)
app.secret_key = "secret123"



USERS_FILE = "users.txt"
RESOURCES_FILE = "resources.txt"
FLASHCARDS_FILE = "flashcards.txt"
LOG_FILE = "usage_log.txt"
active_timers = {}



def log_activity(user, activity):
    with open(LOG_FILE, "a") as f:
        f.write(f"{time.ctime()} - {user} - {activity}\n")



def is_logged_in():
    return "user" in session



@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        attempts = session.get("attempts", 3)
        username = request.form["username"]
        password = request.form["password"]


        with open(USERS_FILE, "r") as f:
            for line in f:
                u, p = line.strip().split("|")
                if u == username and p == password:
                    session["user"] = username
                    session["attempts"] = 3
                    log_activity(username, "Logged in")
                    return redirect("/home")


        attempts -= 1
        session["attempts"] = attempts
        if attempts == 0:
            return "Too many failed attempts. Restart app."
        return f"Invalid login. Attempts left: {attempts}"


    return render_template("login.html")



@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        with open(USERS_FILE, "r") as f:
            for line in f:
                if line.startswith(username + "|"):
                    return "Username already exists"

        with open(USERS_FILE, "a") as f:
            f.write(f"{username}|{password}\n")

        return redirect("/")

    return render_template("register.html")



@app.route("/logout")
def logout():
    user = session["user"]
    log_activity(user, "Logged out")
    session.clear()
    return redirect("/")



@app.route("/home")
def home():
    if not is_logged_in():
        return redirect("/")
    return render_template("home.html")



@app.route("/add_resource", methods=["GET", "POST"])
def add_resource():
    if not is_logged_in():
        return redirect("/")


    if request.method == "POST":
        title = request.form["title"]
        category = request.form["category"]
        url = request.form["url"]
        desc = request.form["description"]


        with open(RESOURCES_FILE, "a") as f:
            f.write(f"{session['user']}|{title}|{category}|{url}|{desc}\n")


        log_activity(session["user"], f"Added resource {title}")
        return redirect("/resources")


    return render_template("add_resource.html")



@app.route("/resources")
def resources():
    if not is_logged_in():
        return redirect("/")


    search = request.args.get("search", "")
    data = []


    with open(RESOURCES_FILE, "r") as f:
        for line in f:
            parts = line.strip().split("|")
            if search.lower() in parts[1].lower():
                data.append(parts)


    return render_template("resources.html", resources=data)



@app.route("/flashcards", methods=["GET", "POST"])
def flashcards():
    if "user" not in session:
        return redirect("/")


    user = session["user"]

    
    if request.method == "POST":
        subject = request.form["subject"]
        unit = request.form["unit"]
        question = request.form["question"]
        answer = request.form["answer"]

        with open(FLASHCARDS_FILE, "a") as f:
            f.write(f"{user}|{subject}|{unit}|{question}|{answer}\n")

        log_activity(user, f"Added flashcard ({subject} - {unit})")
        return redirect(url_for("flashcards"))

    
    selected_subject = request.args.get("subject")
    selected_unit = request.args.get("unit")
    mode = request.args.get("mode")  # "view" or "quiz"


    subjects = {}
    cards = []


    with open(FLASHCARDS_FILE, "r") as f:
        for line in f:
            u, subject, unit, q, a = line.strip().split("|")
            if u != user:
                continue


            subjects.setdefault(subject, set()).add(unit)


            if selected_subject == subject and selected_unit == unit:
                cards.append((q, a))


    quiz_card = None
    if mode == "quiz" and cards:
        quiz_card = random.choice(cards)


    return render_template(
        "flashcards.html",
        subjects=subjects,
        selected_subject=selected_subject,
        selected_unit=selected_unit,
        cards=cards if mode == "view" else [],
        quiz_card=quiz_card,
        mode=mode
    )



@app.route("/contributors")
def contributors():
    if "user" not in session:
        return redirect("/")
    return render_template("contributors.html")



@app.route("/timer", methods=["GET", "POST"])
def timer():
    if not is_logged_in():
        return redirect("/")
 

    user = session["user"]


    if request.method == "POST":
        technique = request.form["technique"]


        if technique == "pomodoro":
            minutes = 25
            name = "Pomodoro"


        elif technique == "fifty":
            minutes = 50
            name = "50–10 Technique"


        else:
            minutes = int(request.form["minutes"])
            name = "Custom"


        def run_timer():
            log_activity(user, f"Started study timer ({name})")
            time.sleep(minutes * 60)
            active_timers[user] = "done"
            log_activity(user, f"Completed study timer ({name})")


        active_timers[user] = "running"
        threading.Thread(target=run_timer, daemon=True).start()


        return render_template(
            "timer.html",
            running=True,
            name=name,
            minutes=minutes
        )


    status = active_timers.get(user)


    if status == "done":
        active_timers.pop(user)
        return render_template("timer.html", done=True)


    return render_template("timer.html")



if __name__ == "__main__":
    app.run(debug=True)
