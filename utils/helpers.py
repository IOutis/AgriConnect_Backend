import os
import uuid
import bcrypt
import jwt
import datetime
import base64
import requests
from supabase import create_client, Client

# Supabase client (shared)
SUPABASE_URL = os.environ.get("SUPABASE_URL") or "https://your-project-url.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or "your-supabase-api-key"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

SECRET_KEY = "your_secret_key"

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed_password):
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def generate_jwt(user_id, role):
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=1)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

# def upload_image_to_supabase(base64_image):
#     image_data = base64.b64decode(base64_image)
#     image_name = f"product-images/{uuid.uuid4()}.jpg"
#     res = supabase.storage.from_("product-images").upload(image_name, image_data)
#     if res.error:
#         raise Exception(res.error.message)
#     return f"{SUPABASE_URL}/storage/v1/object/public/{image_name}"

def fetch_fair_price(
    commodity, 
    # state="Telangana", 
    # district="Hyderabad",
    from_date_str="04-01-2025", 
    to_date_str="04-05-2025", 
    max_data_points=30
):
    API_KEY = "579b464db66ec23bdd0000016d33473f8d42499f462ccd0111ad5373"
    API_URL = "https://api.data.gov.in/resource/35985678-0d79-46b4-9ed6-6f13308a1d24"
    
    from_date = datetime.datetime.strptime(from_date_str, "%d-%m-%Y")
    to_date = datetime.datetime.strptime(to_date_str, "%d-%m-%Y")

    params = {
        "api-key": API_KEY,
        "format": "json",
        # "filters[State.keyword]": state,
        # "filters[District.keyword]": district,
        "filters[Commodity.keyword]": commodity,
        "sort[Arrival_Date]": "desc",
        "limit": 10,
        "offset": 0
    }
    
    modal_prices = []
    offset = 0
    while len(modal_prices) < max_data_points:
        params["offset"] = offset
        response = requests.get(API_URL, params=params)
        # print("→", response.url)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch data. Status code: {response.status_code}")
        
        data = response.json()
        print(data)
        records = data.get("records", [])
        if not records:
            print("records not found")
            break
        
        for record in records:
            price = record.get("Modal_Price")
            if price:
                modal_prices.append(int(price))
            if len(modal_prices) >= max_data_points:
                break
        
        if len(records) < params["limit"]:
            break
        offset += params["limit"]
    
    if not modal_prices:
        # print("MODAL = ", modal_prices)
        return None

    avg_modal_price = sum(modal_prices) / len(modal_prices)
    fair_price = avg_modal_price * 1.10

    return {
        "commodity": commodity,
        "max_price":round(max(modal_prices)/100),
        "min_price":round(min(modal_prices)/100),
        "average_modal_price": round(avg_modal_price, 2),
        "suggested_fair_price": round(fair_price, 2),
        "data_points": len(modal_prices)
    }


# For chat translation using RapidAPI
RAPIDAPI_URL = "https://text-translator2.p.rapidapi.com/translate"
RAPIDAPI_HEADERS = {
    "content-type": "application/x-www-form-urlencoded",
    "X-RapidAPI-Key": "0f491a5108mshbe7b62a9976bafbp15461ejsn7894515d0926",
    "X-RapidAPI-Host": "text-translator2.p.rapidapi.com",
}

def translate_message(message, target_lang="en"):
    data = {
        "source_language": "auto",
        "target_language": target_lang,
        "text": message,
    }
    response = requests.post(RAPIDAPI_URL, data=data, headers=RAPIDAPI_HEADERS)
    if response.status_code == 200:
        translation = response.json()
        return translation["data"]["translatedText"]
    else:
        return message

if __name__=="__main__":
    print(fetch_fair_price("Banana"))