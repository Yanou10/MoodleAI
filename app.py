from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, app, session
import os
import json
from datetime import datetime
from email_utils import envoyer_email
import secrets
from werkzeug.utils import secure_filename
from openai import OpenAI
import time

client = OpenAI()

STORAGE_FILE = "storage.json"
PDF_FOLDER = "static/pdfs"
DATA_FOLDER = "static/data"
THREADS_FILE = "user_threads.json"

def load_user_threads():
    if os.path.exists(THREADS_FILE):
        with open(THREADS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_user_threads(data):
    with open(THREADS_FILE, "w") as f:
        json.dump(data, f, indent=2)


app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

app.config['UPLOAD_FOLDER'] = 'static/pdfs/'

def load_storage():
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_storage(data):
    with open(STORAGE_FILE, "w") as f:
        json.dump(data, f)

storage = load_storage()

if "vector_store_id" not in storage:
    vs = client.vector_stores.create(name="CourseVectorStore")
    storage["vector_store_id"] = vs.id
    save_storage(storage)
vector_store_id = storage["vector_store_id"]

if "file_ids" not in storage:
    storage["file_ids"] = []
if "file_names" not in storage:
    storage["file_names"] = []

file_ids = storage["file_ids"]
file_names = storage["file_names"]
file_streams = []

def try_upload(path):
    """Upload a file to OpenAI only if not already uploaded based on filename."""
    filename = os.path.basename(path)
    if filename in file_names:
        return

    with open(path, "rb") as f:
        uploaded = client.files.create(file=f, purpose="assistants")
        file_ids.append(uploaded.id)
        file_names.append(filename)

    save_storage(storage)



def reupload_file(path):
    """Re-uploads a file even if it already exists in OpenAI, replacing the previous version."""
    filename = os.path.basename(path)

    if filename in file_names:
        index = file_names.index(filename)
        old_id = file_ids[index]
        try:
            client.files.delete(old_id)
        except:
            pass
        file_ids.pop(index)
        file_names.pop(index)

    with open(path, "rb") as f:
        uploaded = client.files.create(file=f, purpose="assistants")
        file_ids.append(uploaded.id)
        file_names.append(filename)

    save_storage(storage)


for root, _, files in os.walk(PDF_FOLDER):
    for fname in files:
        if fname.endswith(".pdf"):
            try_upload(os.path.join(root, fname))

deadlines_path = os.path.join(DATA_FOLDER, "deadlines.json")
if os.path.exists(deadlines_path):
    reupload_file(deadlines_path)

annonces_path = os.path.join(DATA_FOLDER, "annonces.json")
if os.path.exists(annonces_path):
    reupload_file(annonces_path)


if file_streams:
    client.vector_stores.file_batches.upload_and_poll(
        vector_store_id=vector_store_id,
        files=file_streams
    )
    save_storage(storage)

else:
    file_ids = storage["file_ids"]

def handle_file_upload(matiere, titre, deadline, file_stream, filename):
    matiere_path = os.path.join(app.config['UPLOAD_FOLDER'], matiere)
    os.makedirs(matiere_path, exist_ok=True)
    path = os.path.join(matiere_path, filename)

    with open(path, "wb") as f:
        f.write(file_stream.read())

    with open(path, "rb") as f:
        openai_file = client.files.create(file=f, purpose="assistants")

    with open(path, "rb") as f:
        client.vector_stores.file_batches.upload_and_poll(
            vector_store_id=storage["vector_store_id"],
            files=[f]
        )

    
    storage["file_ids"].append(openai_file.id)
    storage["file_names"].append(filename)
    save_storage(storage)

    
    with open('static/data/deadlines.json', 'r') as f:
        deadlines = json.load(f)

    deadlines.append({
        'title': f"{titre} ({matiere})",
        'start': deadline
    })

    with open('static/data/deadlines.json', 'w') as f:
        json.dump(deadlines, f, indent=2)

    return "✅ Upload successful"


if "assistant_id" not in storage:
    assistant = client.beta.assistants.create(
        name="MoodleAI",
        instructions="You are a course assistant that helps students with questions about their uploaded course materials.",
        model="gpt-4o",
        tools=[
            {"type": "file_search"},
            {
                "type": "function",
                "function": {
                    "name": "send_email",
                    "description": "Send an email to a student",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "email": {"type": "string"},
                            "subject": {"type": "string"},
                            "body": {"type": "string"}
                        },
                        "required": ["email", "subject", "body"]
                    }
                }
            },
            {
    "type": "function",
    "function": {
        "name": "upload_course_file",
        "description": "Upload a new course file with subject and optionally add a deadline to the dashboard.",
        "parameters": {
            "type": "object",
            "properties": {
                "matiere": {
                    "type": "string",
                    "enum": ["Maths", "SV"]
                },
                "titre": {"type": "string"},
                "type_doc": {
                    "type": "string",
                    "enum": ["cours", "devoir"]
                },
                "day": {
                    "type": "string",
                    "description": "Weekday (if it's a homework)",
                    "enum": ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
                }
            },
            "required": ["matiere", "titre", "type_doc"]
        }
    }
}
,
            {
                "type": "function",
                "function": {
                    "name": "add_event_to_schedule",
                    "description": "Ajouter un événement ponctuel au calendrier",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "day": {
                                "type": "string",
                                "description": "Jour de la semaine (ex: Lundi)"
                            },
                            "hour": {
                                "type": "string",
                                "description": "Heure au format HH:MM"
                            }
                        },
                        "required": ["title", "day", "hour"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "add_timeframe_to_schedule",
                    "description": "Ajouter une plage horaire au calendrier",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "day": {"type": "string"},
                            "start_hour": {"type": "string"},
                            "end_hour": {"type": "string"}
                        },
                        "required": ["title", "day", "start_hour", "end_hour"]
                    }
                }
            },
            {
    "type": "function",
    "function": {
        "name": "add_reservation",
        "description": "Réserver une salle de travail pour un jour et une heure",
        "parameters": {
            "type": "object",
            "properties": {
                "nom": {"type": "string"},
                "salle": {"type": "string"},
                "jour": {
                    "type": "string",
                    "enum": ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
                },
                "heure": {"type": "string", "description": "Format HH:MM"}
            },
            "required": ["nom", "salle", "jour", "heure"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "add_announcement",
        "description": "Ajouter une annonce pour une matière (Maths ou SV)",
        "parameters": {
            "type": "object",
            "properties": {
                "matiere": {
                    "type": "string",
                    "enum": ["Maths", "SV"]
                },
                "title": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["matiere", "title", "content"]
        }
    }
}

        ],
        tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}}
    )
    storage["assistant_id"] = assistant.id
    save_storage(storage)
else:
    assistant = client.beta.assistants.retrieve(storage["assistant_id"])

def add_announcement(matiere, title, content):
    path = os.path.join("static", "data", "annonces.json")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}

    if matiere not in data:
        data[matiere] = []

    data[matiere].append({"title": title, "content": content})

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    reupload_file(path) 
    return f"✅ Annonce ajoutée pour {matiere}."


def add_to_weekly_schedule(entry):
    schedule_path = os.path.join("static", "data", "weekly_schedule.json")
    try:
        with open(schedule_path, "r", encoding="utf-8") as f:
            schedule = json.load(f)
    except FileNotFoundError:
        schedule = []
    schedule.append(entry)
    with open(schedule_path, "w", encoding="utf-8") as f:
        json.dump(schedule, f, indent=2)


def add_event_to_schedule(title, day, hour):
    today_str = datetime.today().strftime("%Y-%m-%d")
    event_data = {
        "title": title,
        "type": "event",
        "day": day,
        "time": f"{today_str}T{hour}"
    }
    add_to_weekly_schedule(event_data)
    return "✅ Événement ajouté au tableau de bord."

def add_timeframe_to_schedule(title, day, start_hour, end_hour):
    today_str = datetime.today().strftime("%Y-%m-%d")
    event_data = {
        "title": title,
        "type": "timeframe",
        "day": day,
        "start": f"{today_str}T{start_hour}",
        "end": f"{today_str}T{end_hour}"
    }
    add_to_weekly_schedule(event_data)
    return "✅ Plage horaire ajoutée au tableau de bord."



@app.route('/matiere/<nom>')
def matiere(nom):
    pdfs = os.listdir(f'static/pdfs/{nom}')
    try:
        with open(f'static/data/annonces/{nom}.json', 'r') as f:
            annonces = json.load(f)
    except FileNotFoundError:
        annonces = []
    return render_template('matiere.html', nom=nom, pdfs=pdfs, annonces=annonces)

@app.route('/dashboard')
def dashboard():
    with open('static/data/deadlines.json', 'r') as f:
        deadlines = json.load(f)
    with open('static/data/notes.json', 'r') as f:
        notes = json.load(f)
    return render_template('dashboard.html', deadlines=deadlines, notes=notes)

@app.route('/deadlines')
def get_deadlines():
    with open('static/data/deadlines.json') as f:
        data = json.load(f)
    return jsonify(data)

@app.route("/notes")
def notes():
    try:
        with open('static/data/notes.json', 'r') as f:
            notes = json.load(f)
    except FileNotFoundError:
        notes = {}
    return render_template("notes.html", notes=notes)

@app.route("/mail", methods=["GET", "POST"])
def mail():
    if request.method == "POST":
        destinataire = request.form["email"]
        objet = request.form["objet"]
        contenu = request.form["message"]

        if envoyer_email(destinataire, objet, contenu):
            flash("E-mail envoyé avec succès !", "success")
        else:
            flash("Erreur lors de l’envoi de l’e-mail.", "danger")

        return redirect(url_for("mail"))

    return render_template("mail.html")

@app.route("/recherche")
def recherche():
    query = request.args.get("query", "").lower()
    tous_les_cours = [
        "Biologie cellulaire", "Chimie organique", "Mathématiques", 
        "UFR LSH - Histoire", "UFR ST - Informatique", "Physique"
    ]
    resultats = [cours for cours in tous_les_cours if query in cours.lower()]
    matieres = ["CTSPOI", "STSET", "Transversal", "Autres"]
    return render_template("recherche.html", matieres=matieres, resultats=resultats)

@app.route("/chat")
def chat_page():
    thread_id = session.get("thread_id")
    return render_template("chat.html", thread_id=thread_id)

@app.route("/api/chat", methods=["POST"])
def chat():
    thread_id = session.get("thread_id")
    if not thread_id:
        return jsonify({"answer": "❌ No active thread. Please log in again."})

    user_input = request.json.get("question")

    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_input
    )

    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread_id,
        assistant_id=assistant.id
    )

    assistant_message = None
    tool_outputs = []
    print(run.status)
    if run.status == "requires_action":
        for tool in run.required_action.submit_tool_outputs.tool_calls:
            if tool.function.name == "send_email":
                from email_utils import envoyer_email
                args = json.loads(tool.function.arguments)
                envoyer_email(args["email"], args["subject"], args["body"])
                print(args["email"])
                tool_outputs.append({
                    "tool_call_id": tool.id,
                    "output": "📧 Email sent successfully!"
                })

            elif tool.function.name == "upload_course_file":
                args = json.loads(tool.function.arguments)
                storage["pending_upload"] = args
                save_storage(storage)
                tool_outputs.append({
                    "tool_call_id": tool.id,
                    "output": f"📂 Prêt à recevoir le fichier PDF pour {args['titre']} ({args['matiere']}). Veuillez l’envoyer maintenant via le bouton ci-dessous."
                })
            elif tool.function.name == "add_announcement":
                args = json.loads(tool.function.arguments)
                result = add_announcement(args["matiere"], args["title"], args["content"])
                tool_outputs.append({
                    "tool_call_id": tool.id,
                    "output": result
                })
            elif tool.function.name == "add_event_to_schedule":
                args = json.loads(tool.function.arguments)
                result = add_event_to_schedule(args["title"], args["day"], args["hour"])
                tool_outputs.append({
                "tool_call_id": tool.id,
                "output": result
            })

            elif tool.function.name == "add_timeframe_to_schedule":
                args = json.loads(tool.function.arguments)
                result = add_timeframe_to_schedule(args["title"], args["day"], args["start_hour"], args["end_hour"])
                tool_outputs.append({
                    "tool_call_id": tool.id,
                    "output": result
                })

            elif tool.function.name == "add_reservation":
                args = json.loads(tool.function.arguments)
                today_str = datetime.today().strftime("%Y-%m-%d")
                time_str = f"{today_str}T{args['heure']}"
                event_data = {
                    "title": f"Salle {args['salle']} réservée par {args['nom']}",
                    "type": "event",
                    "day": args["jour"],
                    "time": time_str
                }
                path = os.path.join("static", "data", "weekly_schedule.json")
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        schedule = json.load(f)
                except FileNotFoundError:
                    schedule = []
                schedule.append(event_data)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(schedule, f, indent=2)
                reupload_file(path)
                tool_outputs.append({
                    "tool_call_id": tool.id,
                    "output": "✅ Réservation ajoutée au calendrier."
                })

        run = client.beta.threads.runs.submit_tool_outputs_and_poll(
            thread_id=thread_id,
            run_id=run.id,
            tool_outputs=tool_outputs
        )
    print(run.status)
    if run.status == "completed":
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        citations=[]
        for msg in messages.data:
            if msg.role == "assistant" and msg.content and msg.content[0].type == "text":
                
                if tool_outputs:
                    assistant_message = tool_outputs[0]["output"]
                else:
                    text_part = msg.content[0].text
                    for index, annotation in enumerate(text_part.annotations):
                        text_part.value = text_part.value.replace(annotation.text, f"[{index}]")
                        if hasattr(annotation, "file_citation") and annotation.file_citation:
                            cited_file = client.files.retrieve(annotation.file_citation.file_id)
                            citations.append(f"[{index}] {cited_file.filename}")

                    if tool_outputs:
                        assistant_message = tool_outputs[0]["output"]
                    else:
                        assistant_message = text_part.value
                    break
                

    elif run.status == "failed":
        return jsonify({"answer": "❌ Assistant failed."})
    if citations:
        assistant_message += "\n\nSources:\n" + "\n".join(citations)
    return jsonify({"answer": assistant_message or "❌ No response received."})


@app.route("/api/history")
def get_history():
    thread_id = session.get("thread_id")
    if not thread_id:
        return jsonify([])

    messages = client.beta.threads.messages.list(thread_id=thread_id)
    history = []

    for msg in reversed(messages.data):  
        if msg.content and msg.content[0].type == "text":
            role = msg.role
            text = msg.content[0].text.value
            history.append({"role": role, "content": text})

    return jsonify(history)


@app.route('/upload_from_tool', methods=['POST'])
def upload_from_tool():
    thread_id = session.get("thread_id")
    if not thread_id:
        return "❌ No thread found. Please log in again."

    args = storage.pop("pending_upload")
    save_storage(storage)

    fichier = request.files['fichier']
    from io import BytesIO


    matiere_folder = "licence_mathematiques" if args["matiere"] == "Maths" else "sciences_vie"
    path = os.path.join(app.config['UPLOAD_FOLDER'], matiere_folder)
    os.makedirs(path, exist_ok=True)
    filename = secure_filename(args["titre"]) + ".pdf"
    full_path = os.path.join(path, filename)



    with open(full_path, "wb") as f:
        f.write(fichier.read())


    with open(full_path, "rb") as f:
        client.files.create(file=f, purpose="assistants")

    with open(full_path, "rb") as f:
        client.vector_stores.file_batches.upload_and_poll(
            vector_store_id=storage["vector_store_id"],
            files=[f]
        )


    if args["type_doc"] == "devoir" and "day" in args:
        today_str = datetime.today().strftime("%Y-%m-%d")
        event_data = {
            "title": f"📘 {args['titre']} ({args['matiere']})",
            "type": "event",
            "day": args["day"],
            "time": f"{today_str}T10:00"
        }
        schedule_path = os.path.join("static", "data", "weekly_schedule.json")
        try:
            with open(schedule_path, "r", encoding="utf-8") as f:
                schedule = json.load(f)
        except FileNotFoundError:
            schedule = []
        schedule.append(event_data)
        with open(schedule_path, "w", encoding="utf-8") as f:
            json.dump(schedule, f, indent=2)


    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content="The file has been uploaded. Please confirm it's ready and assist me with it."
    )

    followup = client.beta.threads.runs.create_and_poll(
        thread_id=thread_id,
        assistant_id=assistant.id
    )


    messages = client.beta.threads.messages.list(thread_id=thread_id)
    assistant_reply = "✅ File uploaded, but no response from assistant."
    for msg in messages.data:
        if msg.role == "assistant" and msg.content and msg.content[0].type == "text":
            assistant_reply = msg.content[0].text.value
            break

    return render_template("chat.html", message=assistant_reply)



@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        matiere = request.form['matiere']
        titre = request.form['titre']
        fichier = request.files['fichier']
        type_doc = request.form['type']  
        jour = request.form.get('jour', '')

        matiere_folder = 'licence_mathematiques' if matiere == "Maths" else 'sciences_vie'
        path = os.path.join(app.config['UPLOAD_FOLDER'], matiere_folder)
        os.makedirs(path, exist_ok=True)

        full_path = os.path.join(path, secure_filename(fichier.filename))
        fichier.save(full_path)

        
        with open(full_path, "rb") as f:
            client.files.create(file=f, purpose="assistants")

        with open(full_path, "rb") as f:
            client.vector_stores.file_batches.upload_and_poll(
                vector_store_id=storage["vector_store_id"],
                files=[f]
            )

        if type_doc == "devoir" and jour:
            today_str = datetime.today().strftime("%Y-%m-%d")
            event_data = {
                "title": f"📘 {titre} ({matiere})",
                "type": "event",
                "day": jour,
                "time": f"{today_str}T10:00"
            }
            schedule_path = os.path.join("static", "data", "weekly_schedule.json")
            try:
                with open(schedule_path, "r", encoding="utf-8") as f:
                    schedule = json.load(f)
            except FileNotFoundError:
                schedule = []
            schedule.append(event_data)
            with open(schedule_path, "w", encoding="utf-8") as f:
                json.dump(schedule, f, indent=2)

        flash("✅ Fichier téléversé avec succès.")
        return redirect(url_for('index'))

    return render_template('upload.html')

    
@app.route("/licence_mathematiques")
def licence_mathematiques():
    pdfs = os.listdir("static/pdfs/licence_mathematiques") if os.path.exists("static/pdfs/licence_mathematiques") else []
    with open("static/data/annonces.json", "r", encoding="utf-8") as f:
        annonces = json.load(f)
    maths_annonces = annonces.get("Maths", [])
    return render_template("licence_mathematiques.html", pdfs=pdfs, annonces=maths_annonces)

@app.route("/sciences_vie")
def sciences_vie():
    pdfs = os.listdir("static/pdfs/sciences_vie") if os.path.exists("static/pdfs/sciences_vie") else []
    with open("static/data/annonces.json", "r", encoding="utf-8") as f:
        annonces = json.load(f)
    sv_annonces = annonces.get("SV", [])
    return render_template("sciences_vie.html", pdfs=pdfs, annonces=sv_annonces)




@app.route("/reservation", methods=["GET", "POST"])
def reservation():
    if request.method == "POST":
        nom = request.form["nom"]
        salle = request.form["salle"]
        jour = request.form["jour"]
        heure = request.form["heure"]

        today_str = datetime.today().strftime("%Y-%m-%d")
        time_str = f"{today_str}T{heure}"

        event_data = {
            "title": f"Salle {salle} réservée par {nom}",
            "type": "event",
            "day": jour,
            "time": time_str
        }

        schedule_path = os.path.join("static", "data", "weekly_schedule.json")
        try:
            with open(schedule_path, "r", encoding="utf-8") as f:
                schedule = json.load(f)
        except FileNotFoundError:
            schedule = []

        schedule.append(event_data)

        with open(schedule_path, "w", encoding="utf-8") as f:
            json.dump(schedule, f, indent=2)

        return render_template("confirmation.html", nom=nom, date=jour, heure=heure, sujet=f"Salle {salle}")

    return render_template("reservation.html")


    
@app.route('/timetable')
def timetable():
    with open('emplois_du_temps.json') as json_file:
        schedule = json.load(json_file)
    return render_template("timetable.html", schedule=schedule)

@app.route('/login', methods=["POST"])
def login():
    user = request.form.get("user")
    if user:
        session['user'] = user

        user_threads = load_user_threads()

        if user in user_threads:
            session['thread_id'] = user_threads[user]
        else:
            thread = client.beta.threads.create()
            user_threads[user] = thread.id
            session['thread_id'] = thread.id
            save_user_threads(user_threads)

        return redirect(url_for('index'))
    return redirect(url_for('select_user'))


@app.route('/')
def select_user():
    return render_template('select_user.html')

@app.route('/index')
def index():
    user = session.get('user', 'invité')
    matieres = os.listdir('static/pdfs/') if os.path.exists('static/pdfs/') else []
    return render_template('index.html', user=user, matieres=matieres)

@app.route('/get_annonces')
def get_annonces():
    with open('static/data/annonces.json', 'r', encoding='utf-8') as f:
        annonces = json.load(f)
    return jsonify(annonces)


@app.route('/api/add_event', methods=["POST"])
def add_event():
    data = request.get_json()
    filepath = os.path.join("static", "data", "weekly_schedule.json")

    required_fields = ["title", "type", "day"]
    if not all(k in data for k in required_fields):
        return jsonify({"status": "error", "message": "Missing fields"}), 400

    if data["type"] == "event" and "time" not in data:
        return jsonify({"status": "error", "message": "Missing time for event"}), 400
    if data["type"] == "timeframe" and not all(k in data for k in ("start", "end")):
        return jsonify({"status": "error", "message": "Missing start/end for timeframe"}), 400


    with open(filepath, 'r', encoding='utf-8') as f:
        events = json.load(f)

    events.append(data)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(events, f, indent=2)

    return jsonify({"status": "success", "message": "Event added"})

@app.route('/api/schedule')
def get_schedule():
    with open("static/data/weekly_schedule.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)

@app.route("/outils")
def outils():
    return render_template("outils.html")

if __name__ == '__main__':
    app.run(debug=True)

