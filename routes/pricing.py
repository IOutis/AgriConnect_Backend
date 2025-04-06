from flask import Blueprint, request, jsonify
from datetime import datetime
import requests

pricing_bp = Blueprint('pricing', __name__)

# API details
API_KEY = "579b464db66ec23bdd0000016d33473f8d42499f462ccd0111ad5373"
API_URL = "https://api.data.gov.in/resource/35985678-0d79-46b4-9ed6-6f13308a1d24"


# Fetch pricing data for a commodity
@pricing_bp.route('/fetch_price', methods=['GET'])
def fetch_price():
    # Get query params
    state = request.args.get("state", "Telangana")
    district = request.args.get("district", "Hyderabad")
    commodity = request.args.get("commodity", "Tomato")
    from_date_str = request.args.get("from_date", "10-01-2025")
    to_date_str = request.args.get("to_date", "25-01-2025")

    # Convert date strings to datetime objects
    from_date = datetime.strptime(from_date_str, "%d-%m-%Y")
    to_date = datetime.strptime(to_date_str, "%d-%m-%Y")

    # Set API parameters
    params = {
        "api-key": API_KEY,
        "format": "json",
        "filters[State.keyword]": state,
        "filters[District.keyword]": district,
        "filters[Commodity.keyword]": commodity,
        "limit": 1000,
        "offset": 0
    }

    all_records = []
    offset = 0
    limit = 1000

    while True:
        params["offset"] = offset
        response = requests.get(API_URL, params=params)

        if response.status_code == 200:
            data = response.json()
            records = data.get("records", [])

            # Filter records within date range
            for record in records:
                arrival_date_str = record.get("Arrival_Date")
                if arrival_date_str:
                    arrival_date = datetime.strptime(arrival_date_str, "%d/%m/%Y")
                    if from_date <= arrival_date <= to_date:
                        all_records.append(record)

            # Stop fetching if all records are retrieved or no more data is available
            total_records = data.get("total", 0)
            if len(all_records) >= total_records or len(records) < limit:
                break

            offset += limit
        else:
            return jsonify({"error": "Failed to fetch data", "status_code": response.status_code}), 500

    # Sort records by Arrival_Date in descending order
    all_records.sort(
        key=lambda x: datetime.strptime(x.get("Arrival_Date"), "%d/%m/%Y"),
        reverse=True
    )

    # Calculate price statistics (min, max, avg, modal price)
    modal_prices = [int(record.get("Modal_Price", 0)) for record in all_records if record.get("Modal_Price")]

    if not modal_prices:
        return jsonify({"error": "No price data found for the given range"}), 404

    avg_price = sum(modal_prices) / len(modal_prices)
    min_price = min(modal_prices)
    max_price = max(modal_prices)

    return jsonify({
        "commodity": commodity,
        "min_price": min_price,
        "max_price": max_price,
        "average_price": round(avg_price, 2),
        "total_records": len(all_records)
    })
