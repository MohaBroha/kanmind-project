# KanMind 🧠

KanMind is a fullstack Kanban-style productivity application built with Django REST Framework (backend) and a modern frontend.

---

## 🚀 Features

- User Registration API
- User Login with Token Authentication
- Protected User Profile Endpoint (/api/auth/me/)
- Django REST Framework API
- Clean modular backend structure
- Git-clean project setup with proper .gitignore
- Frontend (vanilla HTML/CSS/JS) prepared for integration

---

## 🛠 Tech Stack

### Backend
- Python 3.14
- Django 6
- Django REST Framework
- Token Authentication (DRF)

### Frontend
- HTML5
- CSS3
- JavaScript (Vanilla)

---

## 🔐 Authentication Flow

1. Register user:
POST /api/auth/register/

2. Login user:
POST /api/auth/login/

3. Receive token:
Token <your_token>

4. Use token in requests:
Authorization: Token <your_token>

5. Access protected endpoint:
GET /api/auth/me/

---

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/auth/register/ | POST | Register a new user |
| /api/auth/login/ | POST | Login user and return token |
| /api/auth/me/ | GET | Get current authenticated user |

---

## 📁 Project Structure

KanMind-Project/
│
├── backend/
│   ├── core/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── asgi.py
│   │   ├── wsgi.py
│   │
│   ├── auth_app/
│   │   ├── api/
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── urls.py
│   │   ├── models.py
│   │   ├── migrations/
│   │
│   ├── manage.py
│
├── frontend/
│   ├── pages/
│   ├── shared/
│   ├── assets/
│
├── .gitignore
├── README.md

---

## ⚙️ Setup (Local Development)

Backend:
cd backend
python -m venv env
env\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

---

## 📌 Project Status

✔ Step 6: Authentication System completed (Register, Login, Token Auth, Me endpoint)  
✔ Step 7: Git Cleanup & Professional Setup completed  
🚧 Step 8: Kanban Task System (next phase)

---

## 👨‍💻 Author

Built by MOHA Broha (Fullstack Developer in training)