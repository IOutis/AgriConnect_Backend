from flask import Blueprint, request, jsonify
from utils.helpers import supabase, upload_image_to_supabase, fetch_fair_price

product_bp = Blueprint('product', __name__)

# Upload product with price validation
@product_bp.route('/upload', methods=['POST'])
def upload_product():
    data = request.json
    required_fields = ["farmer_id", "product_name", "commodity", "price", "quantity", ] #"image"
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({"error": f"{field} is required"}), 400

    # Get fair price for the commodity
    fair_price_data = fetch_fair_price(data["product_name"])
    print(fair_price_data)
    if not fair_price_data:
        return jsonify({"error": "Failed to fetch fair price for the commodity"}), 500

    min_price, max_price = fair_price_data["min_price"], fair_price_data["max_price"]
    price = float(data["price"])

    # Check if price is within acceptable range
    if price < min_price or price > max_price:
        return jsonify({"error": f"Price must be between ₹{min_price} and ₹{max_price}"}), 400

    # Upload image to Supabase storage
    # image_url = upload_image_to_supabase(data["image"])

    # Insert product into database
    product_data = {
        "farmer_id": data["farmer_id"],
        "product_name": data["product_name"],
        "commodity": data["commodity"],
        "price": price,
        "quantity": int(data["quantity"]),
        # "image_url": image_url,
        "status": "available"
    }
    try:
        response = supabase.table("products").insert(product_data).execute()
        print("Response from supabse = ",response)
        return jsonify({"message": "Product uploaded successfully", "suggested_price_range": [min_price, max_price]}), 201
    except:
        return jsonify({"error": "Failed to upload product"}), 500

@product_bp.route('/all', methods=['GET'])
def get_all_products():
    response = (
        supabase
        .table("products")
        .select("*, users(name)")  # Join farmers and fetch farmer's name
        .eq("status", "available")
        .order("uploaded_at", desc=True)
        .execute()
    )

    products = []
    if response.data:
        for item in response.data:
            farmer_name = item.get("users", {}).get("name", "Unknown")
            item["farmer_name"] = farmer_name
            item.pop("farmers", None)  # Optional: remove nested 'farmers' field
            products.append(item)

    return jsonify(products), 200


@product_bp.route('/get', methods=['GET'])
def get_product_by_id():
    product_id = request.args.get('id')
    if not product_id:
        return jsonify({"error": "Product ID is required"}), 400

    try:
        response = (
            supabase
            .table("products")
            .select("*, users(name)")  # Join with users table to get farmer name
            .eq("id", product_id)
            .single()  # Ensure one row
            .execute()
        )

        product = response.data
        if not product:
            return jsonify({"error": "Product not found"}), 404

        farmer_name = product.get("users", {}).get("name", "Unknown")
        product["farmer_name"] = farmer_name
        product.pop("users", None)  # Clean up nested users data if needed

        return jsonify(product), 200

    except Exception as e:
        print(f"Error fetching product by ID: {e}")
        return jsonify({"error": "Something went wrong"}), 500
