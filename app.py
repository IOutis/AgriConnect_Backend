import os
from flask import Flask
from flask_cors import CORS
from supabase import create_client, Client
from dotenv import load_dotenv
load_dotenv()
app = Flask(__name__)
CORS(app)

# Supabase configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL") or "https://your-project-url.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or "your-supabase-api-key"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Import your blueprints
from routes.auth import auth_bp
from routes.product import product_bp
from routes.order import order_bp
from routes.dashboard import dashboard_bp  # We’ll adjust the prefix below
from routes.chat import chat_bp

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(product_bp, url_prefix='/api/product')
app.register_blueprint(order_bp, url_prefix='/api/order')
app.register_blueprint(chat_bp, url_prefix='/api/chat')

# Instead of app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard'),
# we use just '/api' so that the routes become /api/farmer/<id> and /api/buyer/<id>
app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')

# Test endpoint
@app.route('/')
def home():
    return "Local host is working! 🚀"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True)
