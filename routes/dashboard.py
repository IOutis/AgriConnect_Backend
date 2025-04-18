from flask import Blueprint, jsonify,request
from utils.helpers import supabase
dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/user', methods=['GET'])
def user_dashboard():
    user_id = request.args.get('user_id')
    print(user_id)
    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    # Fetch user role from users table
    user_response = supabase.table("users").select("role").eq("id", user_id).single().execute()
    user_data = user_response.data

    if not user_data or "role" not in user_data:
        return jsonify({"error": "User not found or role not defined"}), 404

    role = user_data["role"]

    # Fetch unread negotiation messages count (common for all roles)
    unread_response = (
        supabase
        .table("negotiations")
        .select("id")  # just fetch id to keep it lightweight
        .eq("receiver_id", user_id)
        .eq("read", False)
        .execute()
    )
    unread_negotiations = unread_response.data if unread_response.data else []
    unread_count = len(unread_negotiations)

    if role == "consumer":
        # Buyer dashboard
        orders_response = supabase.table("orders").select("*").eq("buyer_id", user_id).execute()
        orders = orders_response.data if orders_response.data else []

        cart_response = supabase.table("carts").select("*").eq("buyer_id", user_id).execute()
        cart_items = cart_response.data if cart_response.data else []

        summary = {
            "role": "consumer",
            "total_orders": len(orders),
            "total_cart_items": len(cart_items),
            "orders": orders,
            "cart_items": cart_items,
            "unread_negotiations": unread_count
        }

    elif role == "farmer":
        # Farmer dashboard
        products_response = supabase.table("products").select("*").eq("farmer_id", user_id).execute()
        products = products_response.data if products_response.data else []

        product_ids = [product["id"] for product in products]

        if product_ids:
            orders_response = supabase.table("orders").select("*").in_("product_id", product_ids).execute()
            orders = orders_response.data if orders_response.data else []
        else:
            orders = []

        total_earnings = sum(order["total_price"] for order in orders ) #if order.get("status") == "completed"

        summary = {
            "role": "farmer",
            "total_products": len(products),
            "total_orders": len(orders),
            "total_earnings": total_earnings,
            "products": products,
            "orders": orders,
            "unread_negotiations": unread_count
        }

    else:
        return jsonify({"error": f"Unsupported role: {role}"}), 400

    return jsonify(summary), 200
