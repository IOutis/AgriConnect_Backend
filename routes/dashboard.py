from flask import Blueprint, jsonify
from utils.helpers import supabase

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/farmer/<farmer_id>', methods=['GET'])
def farmer_dashboard(farmer_id):
    products_response = supabase.table("products").select("*").eq("farmer_id", farmer_id).execute()
    products = products_response.data if products_response.data else []
    product_ids = [product["id"] for product in products]
    if product_ids:
        orders_response = supabase.table("orders").select("*").in_("product_id", product_ids).execute()
        orders = orders_response.data if orders_response.data else []
    else:
        orders = []
    total_earnings = sum(order["total_price"] for order in orders if order.get("status") == "completed")
    summary = {
        "total_products": len(products),
        "total_orders": len(orders),
        "total_earnings": total_earnings,
        "products": products,
        "orders": orders
    }
    return jsonify(summary), 200

@dashboard_bp.route('/buyer/<buyer_id>', methods=['GET'])
def buyer_dashboard(buyer_id):
    orders_response = supabase.table("orders").select("*").eq("buyer_id", buyer_id).execute()
    orders = orders_response.data if orders_response.data else []
    cart_response = supabase.table("carts").select("*").eq("buyer_id", buyer_id).execute()
    cart_items = cart_response.data if cart_response.data else []
    summary = {
        "total_orders": len(orders),
        "orders": orders,
        "cart_items": cart_items
    }
    return jsonify(summary), 200
