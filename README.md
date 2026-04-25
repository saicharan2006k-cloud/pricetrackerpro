# SmartPrice AI 🛒📈

SmartPrice AI is a fully-featured, intelligent price-tracking web application built with Python and Flask. It empowers users to search for live product prices across the web, add items to their personal watchlist, and set up automated email notifications for when prices drop below their target!

## ✨ Key Features

- **Live Product Search:** Real-time web scraping integration using SerpAPI to find the best current deals.
- **User Authentication:** Secure email/password sign-ups and logins with password hashing (`werkzeug.security`) and session management.
- **Smart Price Alerts:** Users can set target prices on products. The backend automatically monitors prices in the background and sends an email notification the moment a price drops!
- **Persistent Cloud Database:** Fully integrated with a PostgreSQL cloud database (Neon) ensuring user data is safely persisted 24/7, even on serverless deployments.
- **Premium User Interface:** A beautiful, responsive, and interactive frontend featuring glassmorphism design, sleek modals, and animated slide-out drawers.

## 🛠️ Technology Stack

- **Backend:** Python, Flask, Flask-SQLAlchemy, Flask-CORS
- **Database:** PostgreSQL (Cloud via Neon), SQLite (Local Fallback)
- **Frontend:** HTML5, Vanilla CSS, Vanilla JavaScript
- **APIs & Integrations:** SerpAPI (Google Shopping Results), `smtplib` (Email Dispatching)
- **Deployment:** Vercel (Serverless Python Functions)

## 🚀 Getting Started (Local Development)

### Prerequisites
- Python 3.10+
- A Google Search API key from [SerpAPI](https://serpapi.com/)
- A free PostgreSQL database from [Neon](https://neon.tech/) (optional, but recommended)

### 1. Clone the repository
```bash
git clone https://github.com/saicharan2006k-cloud/pricetrackerpro.git
cd pricetrackerpro
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file in the root directory and add the following keys:
```env
# Your Google Search API Key
SERPAPI_KEY="your_serpapi_key_here"

# Email Credentials for sending Price Alerts (Use a Google App Password)
EMAIL_USER="your_gmail_address@gmail.com"
EMAIL_PASS="your_16_character_app_password"

# Optional: Connect to your cloud PostgreSQL database (defaults to local SQLite if left blank)
DATABASE_URL="postgresql://user:password@host/database"
```

### 4. Initialize the Database
If you are running the project for the first time or connecting to a new database, generate the tables:
```bash
python -c "from app import db, app; app.app_context().push(); db.create_all()"
```

### 5. Run the Application
```bash
python app.py
```
Your app will now be running at `http://127.0.0.1:5000`!

## 🌍 Deployment (Vercel)

This application is fully optimized for serverless deployment on Vercel.

1. Push your code to a GitHub repository.
2. Log into [Vercel](https://vercel.com/) and import your repository.
3. In the Vercel deployment settings, navigate to **Environment Variables** and add all four keys from your `.env` file (`SERPAPI_KEY`, `EMAIL_USER`, `EMAIL_PASS`, `DATABASE_URL`).
4. Click **Deploy**. Vercel will automatically detect the `vercel.json` configuration and launch your application!
