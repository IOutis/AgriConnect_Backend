import datetime
from flask import Blueprint, request, jsonify
from utils.helpers import supabase, translate_message

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/send', methods=['POST'])
def send_message():
    data = request.json
    required_fields = ["sender_id", "receiver_id", "message"]
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({"error": f"{field} is required"}), 400

    # For simplicity, we're not doing language translation here now
    message_data = {
        "sender_id": data["sender_id"],
        "receiver_id": data["receiver_id"],
        "message": data["message"],
        "sent_at": datetime.datetime.now().isoformat()
    }
    response = supabase.table("chats").insert(message_data).execute()
    if response.data:
        return jsonify({"message": "Message sent successfully"}), 201
    else:
        return jsonify({"error": response.error.message if response.error else "Failed to send message"}), 500

@chat_bp.route('/history/<sender_id>/<receiver_id>', methods=['GET'])
def get_chat_history(sender_id, receiver_id):
    # Fetch messages between the two users
    response = supabase.table("chats").select("*")\
        .or_(f"(sender_id.eq.{sender_id},receiver_id.eq.{receiver_id})", f"(sender_id.eq.{receiver_id},receiver_id.eq.{sender_id})")\
        .order("sent_at", desc=True).execute()
    messages = response.data if response.data else []
    return jsonify(messages), 200
