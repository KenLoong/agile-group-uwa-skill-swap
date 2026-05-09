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
*   **User Authentication:** Secure login/logout with Flask-Login; registration enforces `@student.uwa.edu.au` email and password hashing.
*   **Skill Management (CRUD):** Users can post skills, edit or delete their own listings.
*   **Dynamic Discovery:** Homepage with **jQuery AJAX** category filtering against `/api/filter`, **pagination**, **sort** (newest / most interest), and keyword search (title and description).
*   **Categories:** Normalised **`Category`** table (slug + label) with seed data and Alembic migrations—not a free-text field on posts.
*   **Cover images:** Optional **post cover** upload (validated type/size, stored under `static/uploads/posts/`, ignored by Git except `.gitkeep`).
*   **Rich descriptions:** Post bodies use **Markdown** (rendered with **Bleach** sanitisation). Card previews use plain-text snippets derived from Markdown.
*   **Engagement:** Each post stores **comment** and **like** counts (updated when comments are added or likes toggled). Discovery cards and the post header show both; logged-in users (except the author) can **like/unlike** via AJAX. Sort option **Most likes** is available on Discover.
*   **Public profiles:** **`/user/<username>`** lists that member’s skills — also linked from the **Profile** nav item (your page), author names on cards, comments, and dashboard rows.
*   **For you:** Logged-in users see **recommended skills** from categories they’ve posted in or shown interest in (excluding their own posts and ones they’ve already marked as interested).
*   **Save for later:** Bookmark posts (not your own); manage them under **Dashboard → Saved for later**.
*   **Interaction:** Comments on posts (**AJAX** submit without a full page reload); **Express interest** with dashboard views for **interests received** (who contacted you about your posts) and **my interests** (skills you marked as interested), including contact email for inbound interest.
*   **Security & config:** **CSRF protection** (Flask-WTF) on forms and AJAX `POST`s; `SECRET_KEY` and optional `DATABASE_URL` read from the environment.
*   **UI:** Responsive layouts with **Bootstrap 5** and lightweight **client-side validation** on register, login, and post forms.

---

## 🛠 Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Backend** | Python / Flask |
| **Database** | SQLite + SQLAlchemy (ORM) + Flask-Migrate (Alembic) |
| **Frontend** | HTML5, Jinja2, Bootstrap 5, JavaScript |
| **Interactivity** | jQuery + AJAX |
| **Version Control** | Git / GitHub |

---

## 👥 Team Members

| UWA ID | Name | GitHub Account |
| :--- | :--- | :--- |
| `[24702822]` | Warson | [Warson Long](https://github.com/WarsonLong) |
| `[24319908]` | Dylan | [Yuxuan Xi](https://github.com/dylayXi) |
| `[24920808]` | Shawn | [Shawn Wang](https://github.com/Lipo021) |
| `[24684008]` | Nuwanga | [Nuwanga Niroshan](https://github.com/NuwangaNiroshan) |

---

## 🚀 How to run locally

### Prerequisites
* **Python 3.10+** (3.11+ recommended)
* `pip` (use a **virtual environment**; on macOS/Homebrew Python you may see an “externally managed” error if you skip the venv step)

### 1. Clone and enter the project
```bash
git clone <your-repository-url>
cd demo-for-agile-develop
```
*(Replace the folder name if your clone path differs.)*

### 2. Create and activate a virtual environment
```bash
python3 -m venv .venv
```
**macOS / Linux:**
```bash
source .venv/bin/activate
```
**Windows (cmd):**
```bat
.venv\Scripts\activate.bat
```
**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configuration (optional)

Copy `.env.example` to `.env` and set values (see `.gitignore`: `.env` is not committed):

* **`SECRET_KEY`** — required in production; in development you can omit it to use a built-in insecure default.
* **`DATABASE_URL`** — optional; defaults to `sqlite:///database.db` in the project root.

### 5. Database migrations

Schema is managed with **Flask-Migrate**. After installing dependencies, apply migrations to create or update tables:

```bash
export FLASK_APP=app.py
flask db upgrade
```

On Windows: `set FLASK_APP=app.py` then `flask db upgrade`.

The `migrations/` folder in the repo holds Alembic revision history (evidence of DB migrations for coursework).

### 6. Sample data (optional)

Clears existing rows and inserts demo users/posts/interests. Run **after** `flask db upgrade` so tables exist:

```bash
python seed.py
```

Test logins (after seeding):

* `alice@student.uwa.edu.au` / `password123`
* `bob@student.uwa.edu.au` / `password123`
* `carol@student.uwa.edu.au` / `password123`

### 7. Start the development server

```bash
export FLASK_APP=app.py
python app.py
```

Then open **http://127.0.0.1:5000/** in your browser.

**Alternative — Flask CLI**

```bash
export FLASK_APP=app.py
flask run
```

On Windows, use `set FLASK_APP=app.py` instead of `export`.

### Notes

* The SQLite file is **`database.db`** in the project root (ignored by Git). Each developer keeps their own local file.
* Creating a new migration after model changes: `flask db migrate -m "describe change"` then `flask db upgrade`.

---

## 🧪 Tests

The repository includes:

* **Unit / route tests** — authentication, access control, interest/like toggling, post status, bookmarks, tags, skill matching, @mention notifications, private messaging, and `/api/stats`
* **Selenium browser tests** — register, login/logout, post creation, search, interest UI, @mention comment, stats charts, and private messaging flow

Install test dependencies with:
```bash
pip install -r requirements-dev.txt
```

Run all tests:
```bash
python -m unittest discover tests
```

Run only the unit tests:
```bash
python -m unittest tests.test_unit
```

Run only the Selenium tests:
```bash
python -m unittest tests.test_selenium
```

### Selenium notes

* The Selenium suite starts a **live local Flask server** automatically.
* Install **Chrome/Chromium** and **chromedriver**, or set `CHROMEDRIVER_PATH` if your driver is not on `PATH`.
* If Chromium is installed in a non-standard location, set `CHROME_BIN`.

---

## 📜 Unit Learning Outcomes (CITS5505)
This project demonstrates:
*   Implementation of **Client-Server Architecture**.
*   Proficiency in **Server-side (Flask)** and **Client-side (JS/AJAX)** technologies.
*   Application of **Agile Methodologies** through iterative Git commits.
*   Secure handling of **Data Persistence** and user sessions.
