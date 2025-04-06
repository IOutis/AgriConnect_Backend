from flask import Blueprint, request, jsonify
from utils.helpers import supabase

order_bp = Blueprint('order', __name__)

@order_bp.route('/place', methods=['POST'])
def place_order():
    data = request.json
    required_fields = ["buyer_id", "product_id", "quantity", "price"]
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({"error": f"{field} is required"}), 400

    order_data = {
        "buyer_id": data["buyer_id"],
        "product_id": data["product_id"],
        "quantity": data["quantity"],
        "total_price": float(data["total_price"]),
        "status": "pending"
    }
    response = supabase.table("orders").insert(order_data).execute()
    if response.data:
        return jsonify({"message": "Order placed successfully"}), 201
    else:
        return jsonify({"error": response.error.message if response.error else "Order placement failed"}), 500

@order_bp.route('/my_orders/{consumer_id}', methods=['GET'])
def get_orders_for_buyer(consumer_id):
    response = supabase.table("orders").select("*").eq("buyer_id", consumer_id).execute()
    orders = response.data if response.data else []
    return jsonify(orders), 200

# Cart management
@order_bp.route('/cart/add', methods=['POST'])
def add_to_cart():
    data = request.json
    required_fields = ["buyer_id", "product_id", "quantity"]
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({"error": f"{field} is required"}), 400
    # Check if item already exists can be added here
    cart_data = {
        "buyer_id": data["buyer_id"],
        "product_id": data["product_id"],
        "quantity": data["quantity"]
    }
    response = supabase.table("carts").insert(cart_data).execute()
    if response.data:
        return jsonify({"message": "Item added to cart successfully"}), 201
    else:
        return jsonify({"error": response.error.message if response.error else "Failed to add item"}), 500

@order_bp.route('/cart/<buyer_id>', methods=['GET'])
def get_cart(buyer_id):
    response = supabase.table("carts").select("*").eq("buyer_id", buyer_id).execute()
    cart_items = response.data if response.data else []
    return jsonify(cart_items), 200

@order_bp.route('/cart/remove/<cart_id>', methods=['DELETE'])
def remove_from_cart(cart_id):
    response = supabase.table("carts").delete().eq("id", cart_id).execute()
    if response.data:
        return jsonify({"message": "Item removed from cart"}), 200
    else:
        return jsonify({"error": response.error.message if response.error else "Failed to remove item"}), 500
