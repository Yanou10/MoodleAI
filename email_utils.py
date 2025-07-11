# email_utils.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
load_dotenv()
import os



def envoyer_email(adresse_destinataire, objet, contenu):
    adresse_expediteur = os.getenv("EMAIL_SENDER")
    mot_de_passe = os.getenv("EMAIL_APP_PASSWORD")
    print (adresse_expediteur, mot_de_passe)

    message = MIMEMultipart()
    message["From"] = adresse_expediteur
    message["To"] = adresse_destinataire
    message["Subject"] = objet
    message.attach(MIMEText(contenu, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as serveur:
            serveur.login(adresse_expediteur, mot_de_passe)
            serveur.send_message(message)
        return True
    except Exception as e:
        print("Erreur:", e)
        return False
