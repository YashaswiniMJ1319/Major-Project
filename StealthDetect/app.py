# app.py
import os
import logging
from flask import Flask
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix
from extensions import db   # import db here

logging.basicConfig(level=logging.DEBUG)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "stealth-captcha-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# ---------------- DATABASE LOGIC FOR RAILWAY DEPLOYMENT ----------------
database_url = os.environ.get("DATABASE_URL")
data_dir = os.environ.get("DATA_DIR")  # persistent storage path from Railway plugin (optional)

if not database_url:
    if data_dir:
        # Use Railway persistent volume if provided
        db_path = os.path.join(data_dir, "stealth_captcha.db")
        database_url = f"sqlite:///{db_path}"
    else:
        # Local fallback SQLite
        os.makedirs(os.path.join(os.path.dirname(__file__), "instance"), exist_ok=True)
        database_url = "sqlite:///instance/stealth_captcha.db"
# ------------------------------------------------------------------------

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

with app.app_context():
    import models
    import routes
    db.create_all()

# ------------ REQUIRED FOR PRODUCTION (RAILWAY / HEROKU / RENDER) ------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Railway auto-assigns PORT
    app.run(host="0.0.0.0", port=port)
# -----------------------------------------------------------------------------
