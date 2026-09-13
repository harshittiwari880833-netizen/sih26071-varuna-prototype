# DEPLOYMENT_GUIDE.md
### Zero-knowledge guide: from "code on my laptop" to "live link I can show judges"

This assumes you have never used Git, GitHub, or deployed anything before.
Follow it top to bottom, in order. Every command is copy-pasteable.

---

## PART A — Get a live demo running on YOUR laptop first (do this first, always)

Before touching GitHub or deployment, make sure it works locally — this is
your **guaranteed fallback** even if internet at the venue fails.

1. Install Python if you don't have it: https://www.python.org/downloads/
   (during install on Windows, tick **"Add Python to PATH"**)
2. Open a terminal:
   - **Windows:** search "Command Prompt" or "PowerShell" in the Start menu
   - **Mac:** search "Terminal" in Spotlight
   - **Linux:** Ctrl+Alt+T
3. Navigate into the project folder (replace the path with wherever you saved it):
   ```bash
   cd path/to/sih26071_prototype/frontend
   ```
4. Start the local server:
   ```bash
   python3 -m http.server 8000
   ```
   (On Windows, if `python3` doesn't work, try `python` instead.)
5. Open a browser and go to: **http://localhost:8000**

You should see the VARUNA dashboard. **This is your safety-net demo** —
it needs zero internet once loaded, so it works even with terrible venue wifi.
Keep this running in a terminal tab throughout your presentation.

---

## PART B — Installing Git (one-time setup)

Git is the tool that tracks your code's history and lets you upload
("push") it to GitHub.

1. Download Git: https://git-scm.com/downloads — install with default options.
2. Verify it worked — open a terminal and run:
   ```bash
   git --version
   ```
   You should see something like `git version 2.43.0`. If you see an error,
   restart your terminal/computer and try again.
3. Tell Git who you are (one-time, replace with your info):
   ```bash
   git config --global user.name "Your Name"
   git config --global user.email "your.email@example.com"
   ```

---

## PART C — Create a GitHub account and a repository

1. Go to https://github.com and click **Sign up** if you don't have an account.
2. Once logged in, click the **+** icon (top right) → **New repository**.
3. Fill in:
   - **Repository name:** `sih26071-varuna-prototype` (or any name you like)
   - **Description:** "AI/ML Heavy Rainfall Early Warning & Inundation Prediction — SIH26071"
   - Set to **Public** (so judges/mentors can view it without logging in)
   - **Do NOT** tick "Add a README" (you already have one)
4. Click **Create repository**. GitHub will show you a page with commands —
   ignore it, just follow the steps below instead.

---

## PART D — Push your code to GitHub (do this from your project folder)

Open a terminal, navigate to the **root** of the project folder (the one
containing `README.md`, `frontend/`, `backend/`, `data_pipeline/`):

```bash
cd path/to/sih26071_prototype
```

Then run these commands **one at a time**, in order:

```bash
git init
```
*(sets up Git tracking in this folder)*

```bash
git add .
```
*(stages every file to be saved — the dot means "everything")*

```bash
git commit -m "Initial commit: VARUNA prototype for SIH26071"
```
*(saves a snapshot of your code with a message describing it)*

```bash
git branch -M main
```
*(names your main branch "main", GitHub's default)*

Now connect your local folder to the GitHub repository you created. Copy
the URL of your new repo from GitHub (it looks like
`https://github.com/YOUR-USERNAME/sih26071-varuna-prototype.git`) and run:

```bash
git remote add origin https://github.com/YOUR-USERNAME/sih26071-varuna-prototype.git
```

```bash
git push -u origin main
```

The first time you push, GitHub will ask you to log in — a browser window
usually pops up for you to authenticate. Follow that prompt.

**Done.** Refresh your GitHub repository page in the browser — your code
is now live on GitHub for anyone to view.

### Every time you make changes after this

You don't need to repeat all the steps above. Just run these three,
every time you've changed something and want to save/upload it:

```bash
git add .
git commit -m "Describe what you changed"
git push
```

---

## PART E — Put the LIVE DASHBOARD online (so you have a shareable link)

Your dashboard is a static site (HTML/CSS/JS + a JSON data file) — this
makes it very easy and **free** to host. Recommended: **GitHub Pages**
(zero extra sign-ups, uses the GitHub account you already made).

### Option 1: GitHub Pages (recommended — simplest, free, reliable)

1. Go to your repository on GitHub.
2. Click **Settings** (top menu of the repo) → **Pages** (left sidebar).
3. Under "Build and deployment" → "Source", select **Deploy from a branch**.
4. Under "Branch", select **main**, and folder **/frontend** (if that
   option isn't available, see the note below), then click **Save**.
5. Wait 1-2 minutes. Refresh the page — GitHub will show you a live URL,
   something like:
   `https://YOUR-USERNAME.github.io/sih26071-varuna-prototype/`

**Note:** GitHub Pages' folder dropdown usually only offers `/` (root) or
`/docs`, not arbitrary folder names. If `/frontend` isn't offered as an
option, do this instead (run from your project root):

```bash
git checkout -b gh-pages
git subtree split --prefix frontend -b frontend-only
git push origin frontend-only:gh-pages --force
git checkout main
```

Then in GitHub → Settings → Pages, set Branch to **gh-pages** and folder
to **/ (root)**. Your site will publish from just the frontend folder.

*(If this feels like too much, the simpler fallback is: copy everything
inside your `frontend/` folder to the ROOT of your repository, so
`index.html` sits at the top level. Then GitHub Pages "Deploy from branch:
main, folder: /(root)" works directly, no subtree commands needed.)*

### Option 2: Netlify (also free, drag-and-drop, no Git commands needed)

1. Go to https://app.netlify.com/ and sign up (you can sign up with your
   GitHub account in one click).
2. On the dashboard, find the box that says **"Drag and drop your site
   output folder here"**.
3. Open your file explorer, and drag your entire `frontend` folder into
   that box.
4. Netlify uploads it and gives you a live URL immediately
   (like `https://random-name-123.netlify.app`). You can rename it in
   **Site settings → Change site name**.

This is the fastest option if Git/GitHub Pages feels overwhelming the
night before your presentation.

### Option 3: Vercel (similar to Netlify, also free)

1. Go to https://vercel.com and sign up with GitHub.
2. Click **Add New → Project**, select your GitHub repository.
3. When it asks for the **Root Directory**, set it to `frontend`.
4. Click **Deploy**. You'll get a live URL in about a minute.

---

## PART F — (Optional) Deploying the backend API

Only do this if you specifically want a live API URL to show judges,
separate from the dashboard. **Skip this if you're short on time** — it is
not required for the core demo.

### Render.com (free tier, easiest for a Flask app)

1. Push your code to GitHub first (Parts C & D above).
2. Go to https://render.com and sign up with GitHub.
3. Click **New → Web Service**, select your repository.
4. Set:
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python app.py`
5. Click **Create Web Service**. Render will give you a live URL like
   `https://varuna-backend.onrender.com` after the build finishes
   (~2-3 minutes).
6. Test it by visiting `https://varuna-backend.onrender.com/api/health`
   in your browser — you should see `{"status": "ok", ...}`.

**Note:** Free Render services "sleep" after inactivity and take ~30-60
seconds to wake up on the first request. If demoing this live, hit the
health endpoint a few minutes before your presentation slot to wake it up.

---

## PART G — Presentation-day checklist

- [ ] Local copy running via `python3 -m http.server 8000` on your laptop
      **before you walk on stage** — this is your zero-risk fallback.
- [ ] GitHub repo link ready to paste into chat/PPT if judges ask to see code.
- [ ] Live hosted link (GitHub Pages/Netlify/Vercel) tested on the actual
      wifi/hotspot you'll use during presentation, at least once beforehand.
- [ ] If using the optional backend, ping its `/api/health` endpoint
      5-10 minutes before your slot so it's already "awake."
- [ ] Have the PPT ready to fall back to screenshots/screen-recording of
      the dashboard in case of a total connectivity failure — a 20-second
      screen recording of the working demo, saved locally, is the ultimate
      zero-risk backup.

---

## Common errors and fixes

**"git: command not found"** → Git isn't installed or isn't in your PATH.
Reinstall from https://git-scm.com/downloads and restart your terminal.

**"fatal: remote origin already exists"** → You already ran
`git remote add origin ...` once. Run this instead to update it:
```bash
git remote set-url origin https://github.com/YOUR-USERNAME/YOUR-REPO.git
```

**"Permission denied (publickey)" or login keeps failing** → Use HTTPS
(the `https://github.com/...` URL) rather than SSH, and let the browser
popup handle login — this avoids needing SSH key setup entirely.

**Dashboard shows a red error message about "demo_bundle.json"** → You
opened `index.html` directly by double-clicking it (`file://...` in the
address bar) instead of through `python3 -m http.server`. Browsers block
this for security. Always serve it through a local server or a real
hosting URL, never by double-clicking the file.

**Port 8000 already in use** → Use a different port:
```bash
python3 -m http.server 8080
```
then visit `http://localhost:8080` instead.
