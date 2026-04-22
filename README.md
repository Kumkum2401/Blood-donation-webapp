# Blood Donation Web App

A simple beginner-friendly web app to manage blood donors and emergency blood requests.

## Tech Stack
- Frontend: HTML + CSS
- Backend: Python + Flask
- Database: SQLite
- Container: Docker
- CI/CD: GitHub Actions

## Features
- Donor registration
- Search donors by blood group
- Emergency blood request form
- View all registered donors

## Project Structure
```
blood-donation-webapp/
|-- app.py
|-- requirements.txt
|-- Dockerfile
|-- .github/workflows/ci-cd.yml
|-- static/style.css
|-- templates/
|-- tests/
```

## Run Locally
1. Create virtual environment (optional):
   - `python -m venv .venv`
   - `.venv\Scripts\activate` (Windows)
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Start app:
   - `python app.py`
4. Open browser:
   - [http://localhost:5000](http://localhost:5000)

## Run Tests
- `python -m unittest discover -s tests`

## Run with Docker
1. Build image:
   - `docker build -t blood-donation-webapp .`
2. Run container:
   - `docker run -p 5000:5000 blood-donation-webapp`
3. Open:
   - [http://localhost:5000](http://localhost:5000)

## CI/CD Pipeline
GitHub Actions workflow file: `.github/workflows/ci-cd.yml`

Pipeline steps:
1. Checkout code
2. Setup Python 
3. Install dependencies
4. Run tests
5. Build Docker image
