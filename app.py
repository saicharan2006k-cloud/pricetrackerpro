from flask import Flask, jsonify, request, render_template, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from serpapi import GoogleSearch
from datetime import datetime
import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()
app = Flask(__name__)
app.secret_key = 'smartprice-ai-secret-key'
CORS(app, supports_credentials=True)

# ✅ Email setup
def send_email_alert(user_email, product_title, old_price, new_price, link):
    load_dotenv(override=True)
    sender_email = os.environ.get("EMAIL_USER")
    sender_password = os.environ.get("EMAIL_PASS")
    
    print(f"\n[SIMULATED EMAIL] To: {user_email}")
    print(f"Subject: Price Drop Alert: {product_title}")
    print(f"Price dropped to Rs.{new_price} (Target was Rs.{old_price})! Link: {link}\n")

    if sender_email and sender_password:
        try:
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = user_email
            msg['Subject'] = f"Price Drop Alert: {product_title}"
            body = f"Good news!\n\nThe price of '{product_title}' has dropped to Rs.{new_price} (Target: Rs.{old_price}).\n\nView Deal: {link}\n\n- SmartPrice AI"
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()
            print(f"Real email sent to {user_email}")
        except Exception as e:
            print(f"Failed to send real email: {e}")

# ✅ Database setup
basedir = os.path.abspath(os.path.dirname(__file__))

# Check if a cloud database is provided via environment variables
db_url = os.environ.get("DATABASE_URL")
if db_url:
    # SQLAlchemy requires 'postgresql://' instead of 'postgres://' which many cloud providers use
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
else:
    # Fallback to local SQLite if no cloud database is configured
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'prices.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ✅ Keep API key in environment variable (more secure)
# Run this in terminal before starting app:
# Windows: set SERPAPI_KEY=your-key-here
# Then access it here safely
API_KEY = os.environ.get("SERPAPI_KEY")

if not API_KEY:
    raise ValueError("SERPAPI_KEY environment variable not set")



# ✅ Database Models
class PriceHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    query = db.Column(db.String(200))
    title = db.Column(db.String(500))
    price = db.Column(db.Float)
    site = db.Column(db.String(100))
    date = db.Column(db.DateTime, default=datetime.utcnow)


class Watchlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    title = db.Column(db.String(500))
    price = db.Column(db.String(50))
    site = db.Column(db.String(100))
    image = db.Column(db.String(1000))
    link = db.Column(db.String(1000))
    added_at = db.Column(db.DateTime, default=datetime.utcnow)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)


class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(500))
    price = db.Column(db.String(50))
    site = db.Column(db.String(100))
    link = db.Column(db.String(1000))
    target_price = db.Column(db.Float, nullable=True)
    alert_type = db.Column(db.String(50), default='price') # 'price' or 'restock'
    added_at = db.Column(db.DateTime, default=datetime.utcnow)


# Create tables
from sqlalchemy import text
with app.app_context():
    db.create_all()
    try:
        db.session.execute(text("ALTER TABLE alert ADD COLUMN alert_type VARCHAR(50) DEFAULT 'price'"))
        db.session.commit()
    except Exception:
        db.session.rollback()
    
    try:
        db.session.execute(text('ALTER TABLE watchlist ADD COLUMN user_id INTEGER REFERENCES "user"(id)'))
        db.session.commit()
    except Exception:
        db.session.rollback()


@app.route("/")
def home():
    return render_template("index.html")


def parse_price(price_str):
    # Convert "₹17,399" → 17399.0
    try:
        return float(price_str.replace("₹", "").replace(",", "").strip())
    except:
        return None

def get_direct_link(p):
    """
    Extract the best direct product URL.
    """
    sources = p.get("multiple_sources", [])
    
    # ✅ Fix: make sure sources is actually a list, not True/False
    if isinstance(sources, list) and len(sources) > 0:
        direct = sources[0].get("link", "")
        if direct:
            return direct

    product_link = p.get("product_link", "")
    if product_link:
        return product_link

    return "#"

def get_products(query):
    params = {
        "engine": "google_shopping",
        "q": query,
        "gl": "in",
        "hl": "en",
        "api_key": API_KEY
    }

    search = GoogleSearch(params)
    results = search.get_dict()
    products = results.get("shopping_results", [])

    final = []
    for p in products[:12]:
        title = p.get("title", "N/A")
        price_str = p.get("price", "N/A")
        site = p.get("source", "N/A")
        image = p.get("thumbnail", "")
        link = get_direct_link(p)          # ✅ fixed link extraction
        rating = p.get("rating", None)
        reviews = p.get("reviews", None)
        price_val = parse_price(price_str)
        in_stock = True if price_val else False

        # ✅ Save to database
        if price_val and title != "N/A":
            record = PriceHistory(
                query=query.lower(),
                title=title,
                price=price_val,
                site=site
            )
            db.session.add(record)

        final.append({
            "title": title,
            "price": price_str,
            "site": site,
            "image": image,
            "link": link,
            "rating": rating,
            "reviews": reviews,
            "in_stock": in_stock
        })

    db.session.commit()

    # ✅ Check for price drops for existing alerts
    for p in final:
        title = p["title"]
        price_val = parse_price(p["price"])
        if not price_val: continue
        
        alerts = Alert.query.filter_by(title=title).all()
        for alert in alerts:
            if alert.alert_type == 'price' and alert.target_price and price_val < alert.target_price:
                user = User.query.get(alert.user_id)
                if user:
                    send_email_alert(user.email, title, alert.target_price, price_val, p["link"])
                    alert.target_price = price_val  # Update so we don't keep emailing
                    db.session.commit()
            elif alert.alert_type == 'restock' and price_val > 0:
                user = User.query.get(alert.user_id)
                if user:
                    # Notify about restock
                    send_email_alert(user.email, title, "Out of Stock", price_val, p["link"])
                    # Remove restock alert or change to price alert so it doesn't spam
                    db.session.delete(alert)
                    db.session.commit()

    return final


@app.route("/search")
def search():
    query = request.args.get("q")
    if not query:
        return jsonify({"error": "Enter product name"}), 400
    data = get_products(query)
    return jsonify(data)


@app.route("/history")
def history():
    query = request.args.get("q", "").lower()
    title = request.args.get("title", "")

    records = db.session.query(PriceHistory) \
        .filter(PriceHistory.title == title) \
        .order_by(PriceHistory.date.asc()) \
        .all()

    history_data = []
    for r in records:
        history_data.append({
            "date": r.date.strftime("%d %b %Y %H:%M"),
            "price": r.price,
            "site": r.site
        })

    return jsonify(history_data)

@app.route("/compare")
def compare():
    title = request.args.get("title", "")
    if not title:
        return jsonify([])

    from sqlalchemy import func
    # Get the latest price for each site for this product title
    subq = db.session.query(
        PriceHistory.site,
        func.max(PriceHistory.date).label('max_date')
    ).filter(PriceHistory.title == title).group_by(PriceHistory.site).subquery()

    records = db.session.query(PriceHistory).join(
        subq,
        (PriceHistory.site == subq.c.site) & (PriceHistory.date == subq.c.max_date)
    ).filter(PriceHistory.title == title).all()

    # Sort by lowest price first
    compare_data = []
    for r in records:
        compare_data.append({
            "site": r.site,
            "price": r.price,
            "date": r.date.strftime("%d %b %Y %H:%M")
        })
    compare_data.sort(key=lambda x: x['price'])

    return jsonify(compare_data)


# ── WATCHLIST ────────────────────────────────────────────────
@app.route("/watchlist", methods=["GET"])
def get_watchlist():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    items = Watchlist.query.filter_by(user_id=session["user_id"]).order_by(Watchlist.added_at.desc()).all()
    return jsonify([{
        "id": w.id,
        "title": w.title,
        "price": w.price,
        "site": w.site,
        "image": w.image,
        "link": w.link,
        "added_at": w.added_at.strftime("%d %b %Y")
    } for w in items])


@app.route("/watchlist", methods=["POST"])
def add_watchlist():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    if not data or not data.get("title"):
        return jsonify({"error": "Missing product data"}), 400
    # Avoid duplicates by title for the same user
    existing = Watchlist.query.filter_by(user_id=session["user_id"], title=data["title"]).first()
    if existing:
        return jsonify({"message": "Already in watchlist", "id": existing.id}), 200
    item = Watchlist(
        user_id=session["user_id"],
        title=data.get("title"),
        price=data.get("price", ""),
        site=data.get("site", ""),
        image=data.get("image", ""),
        link=data.get("link", "#")
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({"message": "Added to watchlist", "id": item.id}), 201


@app.route("/watchlist/<int:item_id>", methods=["DELETE"])
def remove_watchlist(item_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    item = Watchlist.query.filter_by(id=item_id, user_id=session["user_id"]).first()
    if not item:
        return jsonify({"error": "Not found"}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Removed"}), 200


# ── BEST DEAL OF THE DAY ─────────────────────────────────────
@app.route("/best-deal")
def best_deal():
    """
    Find the product whose current price is lowest compared to
    its all-time highest price (biggest absolute saving).
    Requires at least 2 data points per product.
    """
    from sqlalchemy import func

    # Get max price ever recorded per title
    subq_max = db.session.query(
        PriceHistory.title,
        func.max(PriceHistory.price).label("max_price")
    ).group_by(PriceHistory.title).subquery()

    # Get latest price per title
    subq_latest = db.session.query(
        PriceHistory.title,
        PriceHistory.site,
        PriceHistory.price.label("current_price"),
        func.max(PriceHistory.date).label("latest_date")
    ).group_by(PriceHistory.title, PriceHistory.site, PriceHistory.price).subquery()

    # Join and compute savings
    results = db.session.query(
        subq_latest.c.title,
        subq_latest.c.site,
        subq_latest.c.current_price,
        subq_max.c.max_price
    ).join(
        subq_max,
        (subq_latest.c.title == subq_max.c.title)
    ).all()

    if not results:
        return jsonify({"error": "No data yet"}), 404

    # Pick product with biggest absolute savings
    best = max(results, key=lambda r: (r.max_price or 0) - (r.current_price or 0))
    savings = (best.max_price or 0) - (best.current_price or 0)

    if savings <= 0:
        return jsonify({"error": "No savings found yet"}), 404

    return jsonify({
        "title": best.title,
        "current_price": best.current_price,
        "highest_price": best.max_price,
        "savings": round(savings, 2),
        "site": best.site
    })


# ── AUTHENTICATION ───────────────────────────────────────────
@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 400
    
    new_user = User(email=email, password_hash=generate_password_hash(password))
    db.session.add(new_user)
    db.session.commit()
    session["user_id"] = new_user.id
    return jsonify({"message": "Signup successful", "email": email}), 201

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password_hash, password):
        session["user_id"] = user.id
        return jsonify({"message": "Login successful", "email": email}), 200
    return jsonify({"error": "Invalid email or password"}), 401

@app.route("/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    return jsonify({"message": "Logged out"}), 200

@app.route("/auth-status", methods=["GET"])
def auth_status():
    if "user_id" in session:
        user = User.query.get(session["user_id"])
        if user:
            return jsonify({"logged_in": True, "email": user.email})
    return jsonify({"logged_in": False})


# ── PRICE ALERTS ─────────────────────────────────────────────
@app.route("/alerts", methods=["GET"])
def get_alerts():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    alerts = Alert.query.filter_by(user_id=session["user_id"]).order_by(Alert.added_at.desc()).all()
    return jsonify([{
        "id": a.id,
        "title": a.title,
        "price": a.price,
        "site": a.site,
        "link": a.link,
        "target_price": a.target_price,
        "alert_type": a.alert_type,
        "added_at": a.added_at.strftime("%d %b %Y")
    } for a in alerts])

@app.route("/alerts", methods=["POST"])
def add_alert():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    if not data or not data.get("title"):
        return jsonify({"error": "Missing product data"}), 400
    
    existing = Alert.query.filter_by(user_id=session["user_id"], title=data["title"]).first()
    if existing:
        return jsonify({"message": "Alert already exists", "id": existing.id}), 200
        
    item = Alert(
        user_id=session["user_id"],
        title=data.get("title"),
        price=data.get("price", ""),
        site=data.get("site", ""),
        link=data.get("link", "#"),
        target_price=data.get("target_price"),
        alert_type=data.get("alert_type", "price")
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({"message": "Alert added", "id": item.id}), 201

@app.route("/alerts/<int:item_id>", methods=["DELETE"])
def remove_alert(item_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    item = Alert.query.filter_by(id=item_id, user_id=session["user_id"]).first()
    if not item:
        return jsonify({"error": "Not found"}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Removed"}), 200

if __name__ == "__main__":
    app.run(debug=True)