from flask import Flask, jsonify, request, render_template
from datetime import datetime
import json
import os

app = Flask(__name__)

# Function to load customer data from the JSON Lines file
def load_customer_data():
    data = []
    try:
        file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'paste.txt'))
        with open(file_path, 'r') as file:
            for line in file:
                if line.strip():  # Skip empty lines
                    data.append(json.loads(line))
        print(f"Loaded {len(data)} customer records")
    except (IOError, json.JSONDecodeError) as e:
        print(f"Error loading customer data: {e}")
        return []
    return data

# Load vendor recommendations from JSON file with error handling
def load_vendor_recommendations():
    file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'vendor_recommendations.json'))
    
    if not os.path.exists(file_path):
        print("Warning: vendor_recommendations.json not found!")
        return []
    
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading vendor_recommendations.json: {e}")
        return []

customer_data = load_customer_data()
vendor_recommendations = load_vendor_recommendations()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/refresh-data', methods=['POST'])
def refresh_data():
    global customer_data, vendor_recommendations
    customer_data = load_customer_data()
    vendor_recommendations = load_vendor_recommendations()
    return jsonify({"message": "Data refreshed successfully", 
                    "customer_count": len(customer_data),
                    "recommendation_count": len(vendor_recommendations)})

@app.route('/customers', methods=['GET'])
def get_customers():
    customer_name = request.args.get('name')
    if customer_name:
        filtered_customers = [c for c in customer_data if c.get("Customer Name") == customer_name]
        if not filtered_customers:
            return jsonify({"message": f"No customer found with name {customer_name}"}), 404
        return jsonify(filtered_customers)
    return jsonify(customer_data)

@app.route('/customers/extensions', methods=['GET'])
def get_customer_extensions():
    customer_extensions = [
        {
            "customer_name": customer.get("Customer Name"), 
            "total_amount": customer.get("total_amount"),
            "average_delay": customer.get("average_delay"),
            "count_invoices": customer.get("count_invoices"),
            "cluster": customer.get("cluster"),
            "extension_days": customer.get("suggested_due_date_extension")
        } 
        for customer in customer_data
    ]
    
    min_extension = request.args.get('min_extension')
    if min_extension:
        try:
            min_days = float(min_extension)
            customer_extensions = [c for c in customer_extensions if c["extension_days"] >= min_days]
        except ValueError:
            return jsonify({"error": "min_extension must be a number"}), 400
    
    return jsonify(customer_extensions)

@app.route('/clusters', methods=['GET'])
def get_clusters():
    clusters = {}
    for customer in customer_data:
        cluster = customer.get("cluster")
        if cluster not in clusters:
            clusters[cluster] = []
        clusters[cluster].append(customer.get("Customer Name"))
    
    cluster_metrics = []
    for cluster_id, customer_names in clusters.items():
        cluster_customers = [c for c in customer_data if c.get("Customer Name") in customer_names]
        
        avg_extension = sum(c.get("suggested_due_date_extension", 0) for c in cluster_customers) / len(cluster_customers)
        avg_delay = sum(c.get("average_delay", 0) for c in cluster_customers) / len(cluster_customers)
        total_invoices = sum(c.get("count_invoices", 0) for c in cluster_customers)
        
        cluster_metrics.append({
            "cluster_id": cluster_id,
            "customer_count": len(customer_names),
            "avg_extension_days": avg_extension,
            "avg_delay_days": avg_delay,
            "total_invoices": total_invoices,
            "customer_names": customer_names
        })
    
    return jsonify(cluster_metrics)

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "The requested resource was not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "An internal server error occurred"}), 500

if __name__ == '__main__':
    app.run(debug=True)
