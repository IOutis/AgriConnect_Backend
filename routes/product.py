from datetime import datetime
from flask import Blueprint, request, jsonify
from utils.helpers import supabase, fetch_fair_price
import requests
import traceback

product_bp = Blueprint('product', __name__)

# Upload product with price validation
@product_bp.route('/upload', methods=['POST'])
def upload_product():
    data = request.json
    required_fields = ["farmer_id", "product_name", "commodity", "price", "quantity","image" ,"lang"] #"image"
    print(data)
    for field in required_fields:
        if field not in data or not data[field]:
            print(field ,"is required")
            return jsonify({"error": f"{field} is required"}), 400

    # Get fair price for the commodity
    lang = data["lang"]
    if (lang!="en"): 
        product_name= text_to_eng_translation(data['product_name'])
        commodity = text_to_eng_translation(data['commodity'])
        units = text_to_eng_translation(data['units'])
    else :
        product_name = data["product_name"]
        commodity = data["commodity"]
        units = data["units"]
        product_name = product_name.title()
    print("Product Name : ",product_name)
    fair_price_data = fetch_fair_price(product_name)
    print(fair_price_data)
    if not fair_price_data:
        return jsonify({"error": "Failed to fetch fair price for the commodity"}), 500

    min_price, max_price = fair_price_data["min_price"], fair_price_data["max_price"]
    price = float(data["price"])

    # Check if price is within acceptable range
    if price < min_price or price > max_price:
        return jsonify({"error": f"Price must be between ₹{min_price} and ₹{max_price}"}), 400

    # Upload image to Supabase storage
    image_url = data["image"]

    # Insert product into database
    product_data = {
        "farmer_id": data["farmer_id"],
        "product_name": product_name,
        "commodity": commodity,
        "price": price,
        "quantity": int(data["quantity"]),
        "image_url": image_url,
        "units":units,
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
    # 1. Get the search terms from query parameters
    # Use distinct names to avoid confusion
    product_name_filter = request.args.get('product_name', None)
    commodity_filter = request.args.get('commodity', None)
    lang = request.args.get('lang',"en")
    print("LANG : ",lang)

    try:
        # 2. Start building the query
        query_builder = (
            supabase
            .table("products")
            .select("*, users(name)")  # Join users table
            .eq("status", "available")
        )

        # 3. --- Apply filters conditionally ---
        # Apply product_name filter if provided
        if product_name_filter and product_name_filter.strip():
            query_builder = query_builder.ilike('product_name', f'%{product_name_filter.strip()}%')

        # Apply commodity filter if provided
        if commodity_filter and commodity_filter.strip():
             # Assuming the column name in your Supabase table is 'commodity'
            query_builder = query_builder.ilike('commodity', f'%{commodity_filter.strip()}%')

        # 4. Add ordering (apply *after* all filtering)
        query_builder = query_builder.order("uploaded_at", desc=True)

        # 5. Execute the final query
        response = query_builder.execute()

        # --- Process the results (This part remains the same) ---
        processed_products = []
        if response.data:
            for item in response.data:
                # Get farmer name
                farmer_name = item.get("users", {}).get("name", "Unknown")
                if lang!="en":
                    item["farmer_name"] = eng_to_des_translation(farmer_name,lang)
                item.pop("users", None)

                # Format date
                timestamp_str = item.get("uploaded_at")
                readable_date = "N/A"
                if timestamp_str:
                    try:
                        dt_object = datetime.fromisoformat(timestamp_str)
                        readable_date = dt_object.strftime("%B %d, %Y at %I:%M %p")
                    except ValueError as e:
                        print(f"Warning: Could not parse date '{timestamp_str}': {e}")
                        readable_date = "Invalid Date"
                item["uploaded_at_readable"] = readable_date
                
                if(lang!="en"):
                    item['product_name_translated']=eng_to_des_translation(item['product_name'],lang)
                    item['commodity_translated']=eng_to_des_translation(item['commodity'],lang)
                    item['units_translated']=eng_to_des_translation(item['units'],lang)
                else :
                    item['product_name_translated']=item['product_name']
                    item['commodity_translated']=item['commodity']
                    item['units_translated']=item['units']

                processed_products.append(item)
        

        return jsonify(processed_products), 200

    except Exception as e:
        # Log the full error
        print(f"Error fetching all products: {e}\n{traceback.format_exc()}")
        return jsonify({"error": "Something went wrong while fetching products"}), 500



@product_bp.route('/get', methods=['GET'])
def get_product_by_id():
    product_id = request.args.get('id')
    lang = request.args.get('lang')

    if not product_id:
        return jsonify({"error": "Product ID is required"}), 400

    try:
        response = (
            supabase
            .table("products")
            .select("*, users(name)")
            .eq("id", product_id)
            .single()
            .execute()
        )

        if "error" in response and response.error:
            return jsonify({"error": response.error.message}), 500

        product = response.data
        if not product:
            return jsonify({"error": "Product not found"}), 404

        # Extract farmer name
        farmer_name = product.get("users", {}).get("name", "Unknown")
        product["farmer_name"] = farmer_name
        product.pop("users", None)

        # Format uploaded_at date
        timestamp_str = product.get("uploaded_at")
        readable_date = "N/A"
        if timestamp_str:
            try:
                dt_object = datetime.fromisoformat(timestamp_str)
                readable_date = dt_object.strftime("%B %d, %Y at %I:%M %p")
            except ValueError as e:
                print(f"Warning: Could not parse date '{timestamp_str}': {e}")
                readable_date = "Invalid Date"

        # Add translations if lang is provided
        if lang and lang != "en":
            product['product_name_translated'] = eng_to_des_translation(product['product_name'], lang)
            product['commodity_translated'] = eng_to_des_translation(product['commodity'], lang)
            product['units_translated'] = eng_to_des_translation(product['units'], lang)
        else :
                    product['product_name_translated']=product['product_name']
                    product['commodity_translated']=product['commodity']
                    product['units_translated']=product['units']
        product["uploaded_at_readable"] = readable_date

        return jsonify(product), 200

    except Exception as e:
        print(f"Error fetching product by ID: {e}")
        return jsonify({"error": "Something went wrong"}), 500
@product_bp.route('/getfarmer', methods=['GET'])
def get_product_by_farmerid():
    farmer_id = request.args.get('farmer_id')
    lang = request.args.get('lang')
    if not farmer_id:
        return jsonify({"error": "Farmer ID is required"}), 400

    try:
        response = (
            supabase
            .table("products")
            .select("*, users(name)")  # Join with users table to get farmer name
            .eq("farmer_id", farmer_id)
            .execute()
        )

        products = response.data
        if not products:
            return jsonify({"error": "No products found for this farmer"}), 404

        # Clean and format each product
        for product in products:
            farmer_name = product.get("users", {}).get("name", "Unknown")
            product["farmer_name"] = farmer_name
            product.pop("users", None)  # Remove nested users data if needed
            timestamp_str = product.get("uploaded_at")
            readable_date = "N/A" # Default value if timestamp is missing or invalid
            if timestamp_str:
                try:
                    # Parse the ISO 8601 timestamp string
                    # Supabase often returns timestamps with timezone info or microseconds.
                    # fromisoformat usually handles this well.
                    dt_object = datetime.fromisoformat(timestamp_str)

                    # Format the datetime object into a readable string
                    # Example Format 1: "April 11, 2025 at 06:48 PM"
                    readable_date = dt_object.strftime("%B %d, %Y at %I:%M %p")

                    # Example Format 2: "11 Apr 2025, 18:48"
                    # readable_date = dt_object.strftime("%d %b %Y, %H:%M")

                    # Example Format 3: Relative time (more complex, often better done frontend)
                    # You would need a library like 'humanize' or calculate the difference
                    # from datetime import timezone
                    # time_diff = datetime.now(timezone.utc) - dt_object
                    # readable_date = f"{humanize.naturaldelta(time_diff)} ago" # Requires 'pip install humanize'

                except ValueError as e:
                    print(f"Warning: Could not parse date '{timestamp_str}': {e}")
                    readable_date = "Invalid Date" # Or keep "N/A" or the original string

            product["uploaded_at_readable"] = readable_date
            if lang!="en": 
                product['product_name_translated']=eng_to_des_translation(product['product_name'],lang)
                product['commodity_translated']=eng_to_des_translation(product['commodity'],lang)
                product['units_translated']=eng_to_des_translation(product['units'],lang)
            else :
                    product['product_name_translated']=product['product_name']
                    product['commodity_translated']=product['commodity']
                    product['units_translated']=product['units']
        return jsonify(products), 200

    except Exception as e:
        print(f"Error fetching products by farmer ID: {e}")
        return jsonify({"error": "Something went wrong"}), 500


def text_to_eng_translation(text):
    url = "https://text-translator2.p.rapidapi.com/translate"
    headers = {
        "content-type": "application/x-www-form-urlencoded",
        "X-RapidAPI-Key": "0f491a5108mshbe7b62a9976bafbp15461ejsn7894515d0926",
        "X-RapidAPI-Host": "text-translator2.p.rapidapi.com",
    }
    data = {
        "source_language": "auto",
        "target_language": "en",
        "text": text,
    }
    response = requests.post(url, data=data, headers=headers)
    translation = response.json()
    translated_text = translation["data"]["translatedText"]
    print(translated_text)
    return translated_text

def eng_to_des_translation(text,desired_lang):
    url = "https://text-translator2.p.rapidapi.com/translate"
    headers = {
        "content-type": "application/x-www-form-urlencoded",
        "X-RapidAPI-Key": "0f491a5108mshbe7b62a9976bafbp15461ejsn7894515d0926",
        "X-RapidAPI-Host": "text-translator2.p.rapidapi.com",
    }
    data = {
        "source_language": "en",
        "target_language": desired_lang,
        "text": text,
    }
    response = requests.post(url, data=data, headers=headers)
    translation = response.json()
    translated_text = translation["data"]["translatedText"]
    print(translated_text)
    return translated_text

@product_bp.route('/edit', methods=['PUT'])
def edit_product():
    data = request.json
    required_fields = ["product_id", "farmer_id", "product_name", "commodity", "price", "quantity", "units"]
    print(data)
    # Validate required fields
    for field in required_fields:
        if field not in data or not data[field]:
            print("error")
            return jsonify({"error": f"{field} is required"}), 400
        

    # Translate for consistency with fair price service
    product_name = text_to_eng_translation(data['product_name'])
    commodity = text_to_eng_translation(data['commodity'])
    units = text_to_eng_translation(data['units'])

    # Get fair price
    fair_price_data = fetch_fair_price(product_name)

# Check if fetch failed or returned error
    fair_price_data = fetch_fair_price(product_name)

# Check if fetch failed or returned error
    if not fair_price_data or "min_price" not in fair_price_data or "max_price" not in fair_price_data:
        print("Fair price data error:", fair_price_data)
        return jsonify({"error": "Failed to fetch valid fair price for the commodity"}), 500


    min_price, max_price = fair_price_data["min_price"], fair_price_data["max_price"]
    price = float(data["price"])
    if price < min_price or price > max_price:
        
        return jsonify({"error": f"Price must be between ₹{min_price} and ₹{max_price}"}), 400

    # Prepare update payload
    update_data = {
        "product_name": product_name,
        "commodity": commodity,
        "price": price,
        "quantity": int(data["quantity"]),
        "units": units,
        # "image": data["image"],
    }

    if "image" in data and data["image"]:  # Optional image update
        update_data["image_url"] = data["image"]

    try:
        response = (
            supabase
            .table("products")
            .update(update_data)
            .eq("id", data["product_id"])
            .eq("farmer_id", data["farmer_id"])  # Ensure only the product owner can update
            .execute()
        )

        # if response.error:
        #     return jsonify({"error": response.error.message}), 500

        return jsonify({
            "message": "Product updated successfully",
            "suggested_price_range": [min_price, max_price]
        }), 200

    except Exception as e:
        import traceback
        print(f"Error updating product: {e}\n{traceback.format_exc()}")
        return jsonify({"error": "Something went wrong during update"}), 500
