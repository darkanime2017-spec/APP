# Online TP Platform

This project contains the full-stack application for the Online TP Platform, including a FastAPI backend and a React frontend.

## Project Structure

The project is organized into two main directories:

- `/backend`: Contains the Python FastAPI application.
- `/frontend`: Contains the React + Vite frontend application.

### Backend Structure

```
backend
│   .env
│   .env.example
│
├───app
│   │   main.py         # FastAPI app entrypoint
│   │   models.py       # SQLAlchemy ORM models
│   │   schemas.py      # Pydantic schemas
│   │   crud.py         # Database functions
│   │   config.py       # Environment config
│   │   db.py           # Database session setup
│   │
│   ├───api             # API endpoint routers
│   │   │   auth.py
│   │   │   upload.py
│   │
│   └───services        # Business logic (Firebase, Drive)
│       │   auth_service.py
│       │   drive_service.py
│
└───secrets
        firebase-credentials.json
        google-credentials.json
```

### Frontend Structure

```
frontend
│   .env
│   package.json
│   vite.config.js
│   ...
│
└───src
    │   App.jsx         # Main app component
    │   main.jsx        # React entrypoint
    │
    ├───components      # Reusable UI components
    ├───context         # React context providers (e.g., Auth)
    ├───hooks           # Custom React hooks
    ├───lib             # API clients, Firebase setup
    └───pages           # Top-level page components
```

## Getting Started

### Backend
1. Navigate to the `backend` directory.
2. Create a virtual environment: `python -m venv venv`
3. Activate it: `source venv/bin/activate` (or `venv\Scripts\activate` on Windows)
4. Install dependencies: `pip install -r requirements.txt` (We should create this file next)
5. Copy `.env.example` to `.env` and fill in your credentials.
6. Run the server: `uvicorn app.main:app --reload`

### Frontend
1. Navigate to the `frontend` directory.
2. Install dependencies: `npm install`
3. Copy `.env.example` to `.env` and fill in your Firebase config.
4. Run the development server: `npm run dev`