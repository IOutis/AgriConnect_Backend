import os
import jwt
import datetime
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from utils.helpers import supabase  # Import your Supabase instance
from routes.product import text_to_eng_translation
auth_bp = Blueprint('auth', __name__)

# Load Secret Key from Environment Variables (Ensure this is set)
SECRET_KEY = os.getenv("SECRET_JWT_KEY", "")  # Change this securely!

# 🔹 Helper Function: Generate JWT Token
def generate_jwt(user_id, role):
    """Generates a JWT token for authentication."""
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=1)  # 🔄 24-hour expiry 
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

# 🔹 User Signup & Auto Login
@auth_bp.route('/signup', methods=['POST'])
def signup():
    data = request.json
    required_fields = ["name", "email", "password", "role", "phone_number","lang"]

    # Validate required fields
    missing_fields = [field for field in required_fields if not data.get(field)]
    if missing_fields:
        return jsonify({"error": f"Missing fields: {', '.join(missing_fields)}"}), 400

    # Hash password before storing
    hashed_password = generate_password_hash(data["password"])
    if(data['lang']!="en"):
        data['name']= text_to_eng_translation(data['name'])
        data['role']= text_to_eng_translation(data['role']).lower()
    # Create user record
    user_data = {
        "name": data["name"],
        "email": data["email"],
        "password": hashed_password,
        "role": data["role"],
        "phone_number": data["phone_number"],
        "preferred_language": data.get("preferred_language", "en")
    }

    # Insert user into Supabase
    response = supabase.table("users").insert(user_data).execute()

    if response.data:
        user = response.data[0]  # Retrieve inserted user
        token = generate_jwt(user["id"], user["role"])  # Generate JWT

        return jsonify({
            "message": "User created successfully",
            "token": token,  # 🔹 Return token for auto-login
            
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "phone_number": user["phone_number"],
            "preferred_language": user.get("preferred_language", "en")
            
        }), 201

    return jsonify({"error": "Signup failed. Try again later."}), 500

# 🔹 User Login
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    # Query Supabase for user
    response = supabase.table("users").select("*").eq("email", email).execute()

    if not response.data:
        return jsonify({"error": "User not found"}), 404

    user = response.data[0]
    # print(user)

    # Verify password
    if not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    # Generate JWT token
    token = generate_jwt(user["id"], user["role"])

    return jsonify({
        "token": token,
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "phone_number": user["phone_number"],
        "preferred_language": user.get("preferred_language", "en")
        
    }), 200

# 🔹 Update Preferred Language
@auth_bp.route('/update_language/<user_id>', methods=['POST'])
def update_language(user_id):
    data = request.json
    new_lang = data.get("preferred_language", "en")

    response = supabase.table("users").update({"preferred_language": new_lang}).eq("id", user_id).execute()

    if response.data:
        return jsonify({"message": "Language updated successfully"}), 200

    return jsonify({"error": "Update failed"}), 500
