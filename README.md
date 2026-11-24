# Customer Review & Feedback App

React + Vite frontend, FastAPI backend, PostgreSQL database, and Brevo email notifications.

## Features
- Mobile-friendly 1–5 star customer rating flow.
- Google review page link and private feedback form are both available to every customer, regardless of rating. Neither option is hidden based on the selected rating.
- Feedback form: name, organization, email, phone, rating, message.
- Feedback stored in PostgreSQL.
- New feedback email notification through Brevo API.
- Admin dashboard at `/admin`, protected by `ADMIN_TOKEN`.
- Dashboard stats and recent submissions.

## Deploy to Render (Blueprint)
1. Push this project to a new GitHub repository.
2. In Render, choose **New + → Blueprint** and connect the repository.
3. Render reads `render.yaml` and creates the PostgreSQL database, API service, and static frontend.
4. During setup, enter:
   - `BREVO_API_KEY`: Brevo API v3 key.
   - `SENDER_EMAIL`: sender email verified in Brevo.
   - `ADMIN_EMAIL`: inbox that should receive feedback notifications.
5. After services are created, open the `customer-review-frontend` service → Environment. Set `VITE_API_URL` to the API service URL, e.g. `https://customer-review-api.onrender.com`. Save and redeploy the frontend.
6. Open the API service → Environment. Set `CORS_ORIGINS` to the frontend URL (e.g. `https://customer-review-frontend.onrender.com`) and redeploy the API.
7. Copy the generated `ADMIN_TOKEN` from the API service environment. Open `https://YOUR-FRONTEND.onrender.com/admin` and sign in with it.

## Manual deploy
Backend:
- Root directory: `backend`
- Build: `pip install -r requirements.txt`
- Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Add the environment variables from `backend/.env.example`.

Frontend:
- Root directory: `frontend`
- Build: `npm install && npm run build`
- Publish directory: `dist`
- Environment: `VITE_API_URL=https://YOUR-BACKEND.onrender.com`

## Brevo setup
In Brevo, create an API key and verify the sender email/domain. Add the key and sender details as Render environment variables. Do not put the API key in frontend code or commit it to GitHub.

## Important
- Render free web services may spin down when idle. A request after inactivity can take longer.
- Free database availability, expiry, backups, and pricing can change; check the current Render dashboard before relying on free-tier persistence for production data.
- Keep the admin token private. Rotate it if it is exposed.
- Google review links are presented to all customers; do not hide or selectively gate public review access based on rating.
