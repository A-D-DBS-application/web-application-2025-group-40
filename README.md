# 📱 Swipr – Student Job Matching Platform

## Project Description

**Swipr** is a web application that connects students with student jobs using a swipe-based matching concept.  
Students can browse job listings and indicate interest, while companies can post vacancies and view matched candidates.

The platform supports:
- Student and company accounts  
- Job listings created by companies  
- Swipe-based matching (like / dislike)  
- Match visibility for both students and companies  

The backend is built with **Flask** and **PostgreSQL (Supabase)**.  
The UI prototype was created using **Lovable**.

---

## Technologies Used

- **Backend:** Python, Flask  
- **Database:** PostgreSQL (Supabase)  
- **Frontend:** Flask templates  
- **Prototype:** Lovable  
- **Version control:** Git & GitHub  

---

## Setup Instructions

### 1. Clone the Repository

    git clone <YOUR_GITHUB_REPO_URL>
    cd web-application-2025-group-40

### 2. Open the Project in VS Code

    code .

Or manually:  
File → Open Folder → select the project folder.

### 3. Create and Activate a Virtual Environment

#### Windows

    python -m venv venv
    venv\Scripts\activate

#### macOS / Linux

    python3 -m venv venv
    source venv/bin/activate

### 4. Install Dependencies

    pip install -r requirements.txt

### 5. Environment Variables

Create a `.env` file in the root directory and add:

    DATABASE_URL=your_supabase_connection_string
    SECRET_KEY=your_secret_key

You can find the Supabase connection string in the Supabase dashboard.

### 6. Run the Flask Application

    python app.py (or python app/app.py)

### 7. Open the Application in Your Browser

    http://127.0.0.1:5000

The Flask application should now be running locally.

---

## User Interface Prototype

The UI prototype was created using **Lovable**.

Prototype link (expires in 7 days): [lovable_prototype](https://preview--can-i-zip.lovable.app/?__lovable_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiWG9XNENJVW1hemVXSTJWYkRQYW84ZUlSTWpsMSIsInByb2plY3RfaWQiOiJkZGQzOTY5My01YThlLTRjYjYtOWZmYi1mZWQyMDU2MzMwYWQiLCJub25jZSI6IjZmODlkZjk2ZTNjMDdhMGEzZTVhYjQwYjNkNjJiODFhIiwiaXNzIjoibG92YWJsZS1hcGkiLCJzdWIiOiJkZGQzOTY5My01YThlLTRjYjYtOWZmYi1mZWQyMDU2MzMwYWQiLCJhdWQiOlsibG92YWJsZS1hcHAiXSwiZXhwIjoxNzY2NzUwMzU3LCJuYmYiOjE3NjYxNDU1NTcsImlhdCI6MTc2NjE0NTU1N30.JQ6MaKcQcCkjvRzD7P6Db64fYtfpMCR8w_EgAiprj2Y)

Screenshots of the prototype and the final Flask application can be found in:

    user_interface/
      lovable_prototype/
      flaskapp_finalversion/

---

## Partner Feedback Session Recordings 
Video 1: https://drive.google.com/file/d/14-gbG2DQlSJVwL0YdKsO-sc6s-O5VOYX/view?usp=sharing 

Video 2: https://drive.google.com/file/d/1LVrqZdZveejJjB-5VphpRAJJWsxdC_3f/view?usp=sharing

---
 
Group 40 

Academic Year 2025–2026

