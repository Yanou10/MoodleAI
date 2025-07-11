# MoodleAI

**MoodleAI** is a Flask-based web application that mimics Moodle while integrating a GPT-4o assistant.  
Students can upload their course files, ask questions about them, manage their weekly schedule, send emails, and more — all from one dashboard.

---

##  Demo

Ask the assistant to **send an email**:

![Send Mail Demo](assets/demo3.gif)

Ask the assistant to **upload a course file**:

![Upload File Demo](assets/demo2.gif)

Then ask it **questions about the uploaded file**:

![Ask Questions Demo](assets/demo1.gif)

---

##  Environment Setup

Before running the app, create or edit a `.env` file at the root of the project with the following content:

```env
EMAIL_SENDER=your_gmail_address@gmail.com
EMAIL_APP_PASSWORD=your_gmail_app_password
OPENAI_API_KEY=your_openai_api_key
