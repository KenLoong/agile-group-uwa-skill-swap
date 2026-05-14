# 🎓 UWA Skill-Swap
### *Connect. Exchange. Excel.*

**UWA Skill-Swap** is a web-based platform designed specifically for University of Western Australia students to exchange knowledge and skills. Whether you are a coding pro looking to learn guitar, or a linguist wanting to understand data science, this platform facilitates peer-to-peer learning through a persistent, user-friendly client-server application.

---

## 📖 Project Overview

### Purpose
In a university environment, students possess diverse talents beyond their primary degree. This application aims to:
*   **Bridge the knowledge gap** between different faculties.
*   **Promote community engagement** within the UWA campus.
*   **Provide a practical utility** for students to find tutors or hobbyist partners without financial barriers.

### Design & Features
*   **User Authentication:** Secure login/logout system with UWA email verification.
*   **Skill Management (CRUD):** Users can post "skills offered," edit their listings, or delete them once a partner is found.
*   **Dynamic Discovery:** A responsive homepage featuring **AJAX-powered filtering** to browse skills by category (e.g., Coding, Languages, Music) without page reloads.
*   **The "Interest" System:** A unique interaction module where users can express interest in a skill. The owner is then notified via their dashboard with the requester's contact details.
*   **User Profiles & Avatars:** Each user has a public profile page where they can upload or change their profile picture, set "want to learn" categories for bidirectional skill matching, and view their own posts.
*   **Messaging:** Private one-to-one conversations between users using Flask-SocketIO for real-time WebSocket-style updates, with AJAX polling retained as a fallback and unread-message badges shown in the UI.
*   **Engagement:** A clean, intuitive UI built with **Bootstrap 5** focusing on accessibility and ease of use.

---

## 🛠 Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Backend** | Python 3.10+ / Flask |
| **Database** | SQLite + SQLAlchemy ORM + Flask-Migrate / Alembic |
| **Frontend** | Jinja templates, HTML5, Bootstrap 5.3, custom CSS (`static/css/main.css`) |
| **Client-side interactivity** | jQuery, AJAX, custom JavaScript |
| **Realtime messaging** | Flask-SocketIO + Socket.IO client |
| **Auth & Forms** | Flask-Login, Flask-WTF, CSRF protection, Werkzeug password hashing |
| **Content safety** | Markdown rendering with sanitisation via Markdown + Bleach |
| **Testing** | Python `unittest`, Flask test client, Socket.IO test client, Selenium |
| **Version Control** | Git / GitHub |

---

## System architecture

This project uses a single Flask application entry point in `app.py`.

The main runtime structure is:

```text
Browser
  ↓ HTTP / AJAX / Socket.IO
Flask app (`app.py`)
  ↓ SQLAlchemy ORM
SQLite database
```

Important files and folders:

| Path | Purpose |
| :--- | :--- |
| `app.py` | Main Flask application, routes, Socket.IO events, CSRF setup, login manager, and migration setup. |
| `models.py` | SQLAlchemy database models such as `User`, `Post`, `Category`, `Tag`, `Comment`, `Interest`, `Notification`, and `Message`. |
| `forms.py` | Flask-WTF form definitions for registration, login, posts, comments, and account/avatar updates. |
| `templates/` | Jinja templates for rendered pages such as the homepage, dashboard, post detail, login/register, profile, stats, and messaging pages. |
| `static/` | CSS, JavaScript, uploaded images, and client-side behaviour. |
| `migrations/` | Flask-Migrate / Alembic migration files for the current database schema. |
| `seed.py` | Demo seed script for local testing and project demonstration. |
| `tests/` | Unit, Socket.IO, avatar, and Selenium test coverage. |

### Request flow

A normal page request follows this path:

```text
User opens a page
→ Flask route in app.py handles the request
→ SQLAlchemy queries data from SQLite
→ Flask renders a Jinja template
→ Browser displays the page
```

AJAX actions, such as filtering posts or expressing interest, follow this path:

```text
Browser JavaScript sends AJAX request
→ Flask route returns JSON
→ JavaScript updates the page without a full reload
```

Messaging uses a WebSocket-first approach:

```text
Conversation page loads Socket.IO client
→ Browser joins a private conversation room
→ New messages are saved to the Message table
→ Server emits `messages:new` to both connected users
→ AJAX polling remains as fallback if WebSocket is unavailable
```

### Main application features

The app includes:

- user registration and login;
- UWA student email format validation;
- profile pages and avatar upload/removal;
- skill post creation, editing, deletion, categories, tags, and status;
- AJAX discover filtering and search;
- comments, mentions, likes, bookmarks, and notifications;
- dashboard recommendations, interests, matches, and charts;
- public statistics page;
- private messaging with Socket.IO real-time updates and polling fallback;
- seed data for demonstration accounts, posts, comments, likes, interests, messages, and avatars.

---

## 👥 Team Members

| UWA ID | Name | GitHub Account |
| :--- | :--- | :--- |
| `[24702822]` | Warson Long | [KenLoong](https://github.com/KenLoong) |
| `[24319908]` | Dylan Yuxuan Xi | [dylayXi](https://github.com/dylayXi) |
| `[24920808]` | Shawn Wang | [Lipo021](https://github.com/Lipo021) |
| `[24684008]` | Nuwanga Niroshan Hewa Wiladdarage | [NuwangaNiroshan](https://github.com/NuwangaNiroshan) |

---

## 🚀 Getting Started

### 1. Prerequisites

Use Python 3.10+.

It is recommended to use a virtual environment.

### 2. Clone and install dependencies

macOS / Linux:

```bash
git clone https://github.com/KenLoong/agile-group-uwa-skill-swap.git
cd agile-group-uwa-skill-swap

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
git clone https://github.com/KenLoong/agile-group-uwa-skill-swap.git
cd agile-group-uwa-skill-swap

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Local environment

For local development, the app has a development fallback secret key. For any shared, marked, or deployed run, set `SECRET_KEY` explicitly.

macOS / Linux:

```bash
export SECRET_KEY="dev-local-secret-for-skill-swap"
```

Windows PowerShell:

```powershell
$env:SECRET_KEY="dev-local-secret-for-skill-swap"
```

The default database is:

```text
sqlite:///database.db
```

You may override it with `DATABASE_URL`.

### 4. Database setup

Apply migrations:

```bash
python -m flask --app app db upgrade
```

This creates or updates the local SQLite database according to the committed migrations.

### 5. Seed demo data

Run:

```bash
python seed.py
```

`seed.py` wipes and repopulates demo data on each run.

It creates:

- demo users;
- categories;
- skill posts;
- tags;
- comments;
- likes;
- bookmarks;
- interests;
- notifications;
- messages;
- dashboard/statistics data;
- copied avatar files for demo users.

The source seed avatar images are stored in:

```text
static/uploads/avatars/
```

### 6. Demo accounts

All demo accounts use the same password:

```text
password123
```

| Email | Example role in demo data |
| :--- | :--- |
| `alice@student.uwa.edu.au` | Coding posts, comments, messages, dashboard data |
| `bob@student.uwa.edu.au` | Language/Yoga posts and messages |
| `carol@student.uwa.edu.au` | Music/Language posts |
| `dave@student.uwa.edu.au` | Sports/Music posts |
| `emma@student.uwa.edu.au` | Language/Sports posts |
| `frank@student.uwa.edu.au` | Coding/Web posts |
| `grace@student.uwa.edu.au` | Other/Language posts |
| `henry@student.uwa.edu.au` | Coding/Music/Other posts |

### 7. Launch the application

Use:

```bash
python app.py
```

The application will be available at:

```text
http://127.0.0.1:5000/
```

Use `python app.py` rather than plain `flask run` when testing messaging, because `app.py` starts the application through `socketio.run(...)`, which supports the Socket.IO messaging layer.

---

## 🧪 Running Tests

This project uses Python `unittest`.

Run the full test suite:

```bash
python -m unittest discover tests -v
```

Run key test groups individually:

```bash
python -m unittest tests.test_unit -v
python -m unittest tests.test_avatar -v
python -m unittest tests.test_socket_messages -v
```

Selenium tests are also included:

```bash
python -m unittest tests.test_selenium -v
```

Selenium tests require a compatible browser and driver setup. They are slower than the unit tests and are usually run separately during final verification.

---

## 📜 Unit Learning Outcomes (CITS5505)
This project demonstrates:
*   Implementation of **Client-Server Architecture**.
*   Proficiency in **Server-side (Flask)** and **Client-side (JS/AJAX)** technologies.
*   Application of **Agile Methodologies** through iterative Git commits.
*   Secure handling of **Data Persistence** and user sessions.
