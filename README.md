# PestSightLog — Flask Edition

A simple pest sighting log for food manufacturing facilities.
Built with Python, Flask, and SQLite.

---

## Default Login

| Username | Password     |
|----------|--------------|
| admin    | changeme123  |

**Change this password immediately after first login.**

---

## Run Locally

1. Install Python 3.10 or higher
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up the database:
   ```
   python setup.py
   ```
4. Start the app:
   ```
   python app.py
   ```
5. Open your browser to: `http://localhost:5000`

---

## Deploy to PythonAnywhere (Free, Always On, No Credit Card)

PythonAnywhere gives you a free public URL at `yourusername.pythonanywhere.com`.

### Step 1 — Create a free account
Go to **pythonanywhere.com** and sign up for a free Beginner account.
No credit card required.

### Step 2 — Upload your files
1. Click the **Files** tab in the PythonAnywhere dashboard
2. Create a new directory called `pestsightlog`
3. Upload all project files into that folder:
   - `app.py`
   - `setup.py`
   - `requirements.txt`
   - The `templates/` folder and all HTML files inside it
   - The `static/` folder and `style.css` inside it

### Step 3 — Open a Bash console
1. Click the **Consoles** tab
2. Click **Bash** to open a terminal
3. Run the following commands:
   ```
   cd pestsightlog
   pip install --user -r requirements.txt
   python setup.py
   ```

### Step 4 — Create a Web App
1. Click the **Web** tab
2. Click **Add a new web app**
3. Click Next through the domain name screen (your free URL is shown here)
4. Select **Flask**
5. Select **Python 3.10** (or latest available)
6. Set the path to: `/home/yourusername/pestsightlog/app.py`
   (replace `yourusername` with your actual PythonAnywhere username)
7. Click **Next**

### Step 5 — Fix the WSGI file
PythonAnywhere creates a WSGI config file. You need to edit it.

1. On the Web tab, find the **WSGI configuration file** link and click it
2. Delete everything in the file
3. Paste this in (replace `yourusername` with your actual username):
   ```python
   import sys
   path = '/home/yourusername/pestsightlog'
   if path not in sys.path:
       sys.path.insert(0, path)
   from app import app as application
   ```
4. Click **Save**

### Step 6 — Reload and visit your site
1. Go back to the **Web** tab
2. Click the green **Reload** button
3. Click your URL at the top (e.g. `yourusername.pythonanywhere.com`)
4. Log in with `admin` / `changeme123`

---

## File Structure

```
pestsightlog/
├── app.py              # All backend code (routes, models, config)
├── setup.py            # Run once to create DB and default admin
├── requirements.txt    # Python dependencies
├── README.md           # This file
├── templates/
│   ├── base.html       # Shared layout (nav, alerts)
│   ├── login.html      # Login page
│   ├── report.html     # Submit a sighting
│   ├── sightings.html  # View all sightings
│   └── users.html      # Admin: manage user accounts
└── static/
    └── style.css       # All styling
```

---

## Adding Users

Log in as admin, click **Manage Users** in the navigation bar, and add users from there.
Regular users can only see their own sightings. Admins see everything.
