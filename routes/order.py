import traceback
from flask import Blueprint, request, jsonify
from utils.helpers import supabase

order_bp = Blueprint('order', __name__)

# --------------------------------------
# Place single order (direct purchase)
# --------------------------------------
@order_bp.route('/place', methods=['POST'])
def place_order():
    data = request.json
    required_fields = ["buyer_id", "product_id", "quantity", "total_price"]
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

# --------------------------------------
# Confirm all cart items as orders
# --------------------------------------

@order_bp.route('/get_order_summary', methods=['GET'])
def get_order_summary():
    buyer_id = request.args.get("buyer_id")
    if not buyer_id:
        return jsonify({"error": "buyer_id is required"}), 400

    # Step 1: Fetch cart items
    cart_response = supabase.table("carts").select("*").eq("buyer_id", buyer_id).execute()
    cart_items = cart_response.data

    if not cart_items:
        return jsonify({"error": "No items in cart"}), 400

    # Step 2: Get product prices from products table
    product_ids = list({item["product_id"] for item in cart_items})
    products_response = supabase.table("products").select("id, product_name, price").in_("id", product_ids).execute()
    products = {prod["id"]: prod for prod in products_response.data}

    # Step 3: Calculate total and build summary
    total_price = 0
    order_summary = []

    for item in cart_items:
        product_id = item["product_id"]
        quantity = int(item["quantity"])
        product = products.get(product_id)

        if not product:
            continue  # skip missing product info

        price_per_unit = float(product["price"])
        item_total = price_per_unit * quantity
        total_price += item_total

        order_summary.append({
            # "product_id": product_id,
            "product_name": product["product_name"],
            "quantity": quantity,
            "price_per_unit": price_per_unit,
            "total_price": round(item_total, 2)
        })

    return jsonify({
        "total_price": round(total_price, 2),
        "order_summary": order_summary
    }), 200

@order_bp.route('/confirm_order', methods=['POST'])
def confirm_order():
    data = request.json
    buyer_id = data.get("buyer_id")

    if not buyer_id:
        return jsonify({"error": "buyer_id is required"}), 400

    # Step 1: Fetch cart items
    cart_response = supabase.table("carts").select("*").eq("buyer_id", buyer_id).execute()
    cart_items = cart_response.data

    if not cart_items:
        return jsonify({"error": "No items in cart to place order"}), 400

    # Step 2: Get product prices
    product_ids = list({item["product_id"] for item in cart_items})
    products_response = supabase.table("products").select("id, product_name, price").in_("id", product_ids).execute()
    products = {prod["id"]: prod for prod in products_response.data}

    # Step 3: Build order entries
    total_price = 0
    order_entries = []

    for item in cart_items:
        product_id = item["product_id"]
        quantity = int(item["quantity"])
        product = products.get(product_id)

        if not product:
            continue  # skip if product info missing

        price_per_unit = float(product["price"])
        item_total = price_per_unit * quantity
        total_price += item_total

        order_entries.append({
            "buyer_id": buyer_id,
            "product_id": product_id,
            "quantity": quantity,
            "total_price": item_total,
            "status": "pending"
        })

    # Step 4: Insert orders
    supabase.table("orders").insert(order_entries).execute()

    # Step 5: Clear cart
    supabase.table("carts").delete().eq("buyer_id", buyer_id).execute()

    return jsonify({
        "message": "Order placed successfully",
        "orders_created": len(order_entries),
        "total_price": round(total_price, 2)
    }), 201



# --------------------------------------
# View orders placed by a buyer
# --------------------------------------
@order_bp.route('/my_orders', methods=['GET'])
def get_orders_for_buyer():
    buyer_id = request.args.get('buyer_id')
    print(buyer_id)
    if not buyer_id:
        print("BUYER ERROR",buyer_id)
        return jsonify({"error": "buyer_id query parameter is required"}), 400

    # Step 1: Get orders
    response = supabase.table("orders").select("*").eq("buyer_id", buyer_id).execute()
    orders = response.data if response.data else []

    if not orders:
        return jsonify([]), 200

    # Step 2: Get unique product IDs from orders
    product_ids = list(set(order["product_id"] for order in orders))

    # Step 3: Fetch product details (name + image_url)
    product_response = supabase.table("products").select("id, product_name, image_url").in_("id", product_ids).execute()
    products = product_response.data if product_response.data else []

    # Step 4: Create product_id -> {name, image_url} mapping
    product_info_map = {p["id"]: {"product_name": p["product_name"], "image_url": p.get("image_url", "")} for p in products}

    # Step 5: Append product info to each order
    enriched_orders = []
    for order in orders:
        product_info = product_info_map.get(order["product_id"], {"product_name": "Unknown", "image_url": ""})
        order["product_name"] = product_info["product_name"]
        order["image_url"] = product_info["image_url"]
        enriched_orders.append(order)
    print(enriched_orders)
    return jsonify(enriched_orders), 200


# --------------------------------------
# View orders received by a farmer
# --------------------------------------
@order_bp.route('/farmer_orders', methods=['GET'])
def get_orders_for_farmer():
    farmer_id = request.args.get('farmer_id')
    if not farmer_id:
        return jsonify({"error": "farmer_id query parameter is required"}), 400

    # Step 1: Get product IDs by this farmer
    product_response = supabase.table("products").select("id").eq("farmer_id", farmer_id).execute()
    if not product_response.data:
        return jsonify([]), 200

    product_ids = [p["id"] for p in product_response.data]

    # Step 2: Get orders for those products
    order_response = supabase.table("orders").select("*").in_("product_id", product_ids).execute()
    orders = order_response.data if order_response.data else []

    return jsonify(orders), 200
@order_bp.route('/product_orders', methods=['GET'])
def get_orders_for_product():
    product_id = request.args.get('product_id')
    if not product_id:
        return jsonify({"error": "product_id query parameter is required"}), 400

    try:
        order_response = supabase.table("orders").select("*").in_("product_id", [product_id]).execute()
        orders = order_response.data if order_response.data else []
        return jsonify(orders), 200
    except Exception as e:
        print(f"Error fetching product orders: {e}")
        return jsonify({"error": "Something went wrong"}), 500

# --------------------------------------
# Add item to cart
# --------------------------------------
@order_bp.route('/cart/add', methods=['POST'])
def add_to_cart():
    data = request.json
    required_fields = ["buyer_id", "product_id", "quantity"]
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({"error": f"{field} is required"}), 400

    cart_data = {
        "buyer_id": data["buyer_id"],
        "product_id": data["product_id"],
        "quantity": data["quantity"],
        # "price": float(data.get("price", 0))  # optional price field
    }
    response = supabase.table("carts").insert(cart_data).execute()
    if response.data:
        return jsonify({"message": "Item added to cart successfully"}), 201
    else:
        return jsonify({"error": response.error.message if response.error else "Failed to add item"}), 500

# --------------------------------------
# View cart items
# --------------------------------------
@order_bp.route('/cart', methods=['GET'])
def get_cart():
    buyer_id = request.args.get('buyer_id')
    if not buyer_id:
        return jsonify({"error": "buyer_id query parameter is required"}), 400

    # Join with products table and select only needed fields
    response = supabase.table("carts").select("id, quantity, product_id(id, product_name, commodity, price,units)").eq("buyer_id", buyer_id).execute()

    # if response.error:
    #     return jsonify({"error": response.error.message}), 500

    cart_items = []
    for item in response.data:
        product = item.get("product_id", {})
        cart_items.append({
            "cart_id": item["id"],
            "product_id": product.get("id"),
            "product_name": product.get("product_name"),
            "commodity": product.get("commodity"),
            "price": product.get("price"),
            "quantity": item["quantity"]
        })
    print(cart_items)

    return jsonify(cart_items), 200

# --------------------------------------
# Remove item from cart
# --------------------------------------
@order_bp.route('/cart/remove', methods=['DELETE'])
def remove_from_cart():
    cart_id = request.args.get('cart_id')
    if not cart_id:
        return jsonify({"error": "cart_id query parameter is required"}), 400

    response = supabase.table("carts").delete().eq("id", cart_id).execute()
    if response.data:
        return jsonify({"message": "Item removed from cart"}), 200
    else:
        return jsonify({"error": response.error.message if response.error else "Failed to remove item"}), 500


@order_bp.route('/negotiation/details', methods=['GET'])
def get_negotiation_details():
    product_id = request.args.get("product_id")
    buyer_id = request.args.get("buyer_id")

    if not product_id or not buyer_id:
        return jsonify({"error": "product_id and buyer_id are required"}), 400

    # Fetch product
    product_res = supabase.table("products").select("*").eq("id", product_id).single().execute()
    product = product_res.data

    if not product:
        return jsonify({"error": "Product not found"}), 404

    # Fetch farmer
    farmer_id = product.get("farmer_id")
    farmer_res = supabase.table("users").select("id, name, phone_number").eq("id", farmer_id).single().execute()
    farmer = farmer_res.data

    # Fetch consumer
    consumer_res = supabase.table("users").select("id, name, phone_number").eq("id", buyer_id).single().execute()
    consumer = consumer_res.data

    return jsonify({
        "product_details": product,
        "farmer_details": farmer,
        "user_details": consumer
    }), 200
    

@order_bp.route('/negotiation/send', methods=['POST'])
def send_negotiation_message():
    data = request.json
    product_id = data.get("product_id")
    sender_id = data.get("sender_id")
    receiver_id = data.get("receiver_id")
    suggested_price = data.get("suggested_price")
    justification = data.get("justification")
    quantity = data.get("quantity")

    if not all([product_id, sender_id, receiver_id, suggested_price, justification, quantity]):
        return jsonify({"error": "All fields are required"}), 400

    # Insert and get response
    insert_response = supabase.table("negotiations").insert({
        "product_id": product_id,
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "suggested_price": suggested_price,
        "justification": justification,
        "status": "pending",
        "quantity":quantity
    }).execute()

    # if insert_response.error:
    #     return jsonify({"error": "Failed to send negotiation"}), 500

    # Return the first inserted row
    inserted_row = insert_response.data[0] if insert_response.data else {}
    print(inserted_row)
    return jsonify(inserted_row), 201

@order_bp.route('/negotiation/accept', methods=['POST'])
def accept_negotiation():
    data = request.json
    negotiation_id = data.get("negotiation_id")
    buyer_id = data.get("buyer_id")
    quantity = data.get("quantity")

    if not all([negotiation_id, buyer_id, quantity]):
        return jsonify({"error": "Missing required fields"}), 400

    # Get negotiation details
    negotiation_res = (
        supabase
        .table("negotiations")
        .select("*")
        .eq("id", negotiation_id)
        .single()
        .execute()
    )

    negotiation = negotiation_res.data
    if not negotiation:
        return jsonify({"error": "Negotiation not found"}), 404

    # Mark negotiation as accepted
    supabase.table("negotiations").update({"status": "accepted"}).eq("id", negotiation_id).execute()

    # Create order
    order = {
        "buyer_id": buyer_id,
        "product_id": negotiation["product_id"],
        "quantity": quantity,
        "total_price": negotiation["suggested_price"] * quantity,
        "negotiated_price": negotiation["suggested_price"],
        "status": "confirmed"
    }

    # ✅ Correct way to return the inserted row
    order_insert = (
        supabase
        .table("orders")
        .insert(order, returning="representation")
        .execute()
    )

    return jsonify({
        "message": "Negotiation accepted and order placed",
        "order": order_insert.data[0] if order_insert.data else {}
    }), 201

# @order_bp.route('/negotiation/reject', methods=['POST'])
# def reject_negotiation():
#     data = request.json
#     negotiation_id = data.get("negotiation_id")

#     if not negotiation_id:
#         return jsonify({"error": "negotiation_id is required"}), 400

#     supabase.table("negotiations").update({"status": "rejected"}).eq("id", negotiation_id).execute()

#     return jsonify({"message": "Negotiation rejected"}), 200
@order_bp.route('/negotiation/messages', methods=['GET'])
def get_negotiation_messages():
    product_id = request.args.get("product_id")
    user_id = request.args.get("user_id")
    other_user_id = request.args.get("other_user_id")

    if not product_id:
        return jsonify({"error": "product_id is required"}), 400

    # Build filter dynamically
    filters = f"product_id.eq.{product_id}"
    if user_id and other_user_id:
        filters += f",or=(and(sender_id.eq.{user_id},receiver_id.eq.{other_user_id}),and(sender_id.eq.{other_user_id},receiver_id.eq.{user_id}))"

    response = supabase.table("negotiations") \
        .select("*") \
        .match({"product_id": product_id}) \
        .order("timestamp", desc=False) \
        .execute()

    return jsonify(response.data), 200


from datetime import datetime

@order_bp.route('/negotiation/threads', methods=['GET'])
def get_negotiation_threads():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    try:
        # Step 1: Get all negotiations where user is involved
        response = supabase.table("negotiations").select("*").or_(
            f"sender_id.eq.{user_id},receiver_id.eq.{user_id}"
        ).order("timestamp", desc=True).execute()

        if hasattr(response, "error") and response.error:
            return jsonify({"error": "Failed to fetch negotiations"}), 500

        all_negotiations = response.data

        # Step 2: Group by product_id + other_user_id to get threads
        seen_threads = set()
        threads = []

        for n in all_negotiations:
            product_id = n["product_id"]
            other_user_id = n["receiver_id"] if n["sender_id"] == user_id else n["sender_id"]
            thread_key = f"{product_id}-{other_user_id}"

            if thread_key in seen_threads:
                continue

            seen_threads.add(thread_key)

            # Get product and user info
            product = supabase.table("products").select("product_name, image_url").eq("id", product_id).single().execute().data
            user = supabase.table("users").select("name").eq("id", other_user_id).single().execute().data

            # Format the last_updated time
            timestamp_str = n.get("timestamp")
            readable_date = "N/A"
            if timestamp_str:
                try:
                    dt_object = datetime.fromisoformat(timestamp_str)
                    readable_date = dt_object.strftime("%B %d, %Y at %I:%M %p")
                except ValueError as e:
                    print(f"Warning: Could not parse date '{timestamp_str}': {e}")
                    readable_date = "Invalid Date"

            threads.append({
                "thread_id": thread_key,
                "product_id": product_id,
                "product_name": product.get("product_name", ""),
                "product_image": product.get("image_url", ""),
                "other_user_id": other_user_id,
                "other_user_name": user.get("name", "Unknown"),
                "last_message": n["justification"],
                "last_price": n["suggested_price"],
                "last_updated_non_readable": n["timestamp"],
                "last_updated": readable_date  # 👈 New readable time
            })

        return jsonify(threads), 200

    except Exception as e:
        print(f"Error fetching negotiation threads: {e}\n{traceback.format_exc()}")
        return jsonify({"error": "Something went wrong while fetching threads"}), 500

