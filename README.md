# PulseForm API

Backend service for **PulseForm** — a survey & feedback platform. A simplified version of tools like Google Forms, Typeform, or SurveyMonkey: someone builds a survey, shares a link, people answer, and the results come back as live, readable summaries.

This repository contains the REST API built with **Python & FastAPI**. The frontend lives in a separate repo: [`PulseForm-Web`](https://github.com/blearthysenii/PulseForm-Web).

---

## ✨ What it does

PulseForm is built around two core ideas:

- A **survey** is a set of ordered questions, each with a type: multiple choice, rating scale (e.g. 1–5), or free text.
- A **response** is one person's set of answers to that survey.

The API powers the full product loop: **Build → Share → Collect → Analyze.**

## 🧩 Core features

| Feature                    | Description                                                                                                                               |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| **Auth & user roles**      | Creators and admins sign in (JWT). Respondents can answer without an account.                                                             |
| **Survey builder**         | Create a survey with title & description; add, edit, reorder, and remove questions.                                                       |
| **Question types**         | At least three: multiple choice (single or multi pick), rating scale, free text.                                                          |
| **CSV import**             | Upload a CSV file to create many questions at once.                                                                                       |
| **Publishing & sharing**   | Publish a survey to get a shareable link; open/close it to new responses.                                                                 |
| **Collecting responses**   | Each submission is stored as a single response tied to its survey. Required questions are validated before accepting.                     |
| **Results dashboard data** | Aggregated stats per question: counts for choices, distributions for scales, response totals, and free-text answers gathered for reading. |

## 👤 Roles

- **Creator** — builds and owns surveys; only sees results of their own surveys.
- **Respondent** — answers a shared survey (anonymous or signed in); never sees results.
- **Admin** — oversees the platform: all surveys and accounts, for moderation and support.

---

## 🛠 Tech stack

- **Python 3.11+**
- **FastAPI** — web framework
- **SQLAlchemy** — ORM
- **Pydantic** — request/response validation
- **MySQL** — relational database
- **PyMySQL** — MySQL database driver
- **JWT** (`python-jose`) + `passlib[bcrypt]` — authentication
- **Alembic** — database migrations
- **pytest** — testing

## 📁 Project structure

```
PulseForm-API/
├── app/
│   ├── main.py              # FastAPI app entrypoint
│   ├── core/                # config, security (JWT, hashing)
│   ├── models/              # SQLAlchemy models (User, Survey, Question, Response, Answer)
│   ├── schemas/             # Pydantic schemas
│   ├── api/
│   │   ├── auth.py          # register / login
│   │   ├── surveys.py       # survey CRUD, publish, CSV import
│   │   ├── responses.py     # submit & store responses
│   │   └── results.py       # aggregated results per survey
│   └── services/            # business logic (validation, aggregation)
├── alembic/                 # migrations
├── tests/
├── requirements.txt
├── .env.example
└── README.md
```

## 🚀 Getting started

### 1. Clone & create a virtual environment

```bash
git clone https://github.com/blearthysenii/PulseForm-API.git
cd PulseForm-API
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

Linux / Mac

```bash
cp .env.example .env
```

Windows

```bash
copy .env.example .env
```

```env
DATABASE_URL=mysql+pymysql://root:password@localhost/pulseform
SECRET_KEY=change-me
ACCESS_TOKEN_EXPIRE_MINUTES=60
CORS_ORIGINS=http://localhost:5173
```

### 4. Run migrations & start the server

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`.
Interactive docs: **Swagger UI** at `http://localhost:8000/docs`.

## 📡 API overview

| Method  | Endpoint                         | Description               | Auth    |
| ------- | -------------------------------- | ------------------------- | ------- |
| `POST`  | `/auth/register`                 | Create an account         | —       |
| `POST`  | `/auth/login`                    | Get a JWT token           | —       |
| `GET`   | `/surveys`                       | List my surveys           | Creator |
| `POST`  | `/surveys`                       | Create a survey           | Creator |
| `PUT`   | `/surveys/{id}`                  | Edit survey & questions   | Creator |
| `POST`  | `/surveys/{id}/questions/import` | Import questions from CSV | Creator |
| `POST`  | `/surveys/{id}/publish`          | Publish / get share link  | Creator |
| `PATCH` | `/surveys/{id}/status`           | Open / close responses    | Creator |
| `GET`   | `/s/{share_token}`               | Public survey view        | —       |
| `POST`  | `/s/{share_token}/responses`     | Submit a response         | —       |
| `GET`   | `/surveys/{id}/results`          | Aggregated results        | Creator |

## 🗃 Data modeling note

A key design challenge of this project: **different question types have different answer shapes** — a chosen option, a number, or a block of text. The `Answer` model stores all of them in one consistent structure (e.g. nullable columns per shape, or a JSON value column) so every question type fits the same pipeline. Deciding and defending this design is part of the capstone.

## 👥 Team

- [Abit Hyseni](https://github.com/biti222)
- [Flamur Avdylaj](https://github.com/avdylaj-flamur)
- [Bleart Hyseni](https://github.com/blearthysenii)
- [Elijon Rexhepi](https://github.com/ElionR)

## 🎓 Mentor

- Labinot Jaha

Project developed as part of the Intern Capstone Project.

## 🧪 Tests

```bash
pytest
```

## 🔗 Related

- Frontend: [`PulseForm-Web`](https://github.com/blearthysenii/PulseForm-Web)
