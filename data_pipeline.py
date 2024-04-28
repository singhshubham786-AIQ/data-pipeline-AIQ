import pandas as pd
import requests
import json
import matplotlib.pyplot as plt
import pymysql
import cryptography

# API endpoints and credentials (replace with your own)
JSONPLACEHOLDER_API = "https://jsonplaceholder.typicode.com/users"
OPENWEATHERMAP_API = "https://api.openweathermap.org/data/2.5/weather"
OPENWEATHERMAP_API_KEY = "04a760f134c211b4c30289d01089645f"  # Obtain from OpenWeatherMap

# Load sales data from CSV
sales_data = pd.read_csv("sales_data.csv")
sales_data.head()

# Function to fetch user data from JSONPlaceholder API
def get_user_data():
    response = requests.get(JSONPLACEHOLDER_API)
    if response.status_code == 200:
        return json.loads(response.text)
    else:
        raise Exception(f"Error fetching user data: {response.status_code}")

# Function to fetch weather data from OpenWeatherMap API
def get_weather_data(lat, lng):
    url = f"{OPENWEATHERMAP_API}?lat={lat}&lon={lng}&appid={OPENWEATHERMAP_API_KEY}&units=metric"
    response = requests.get(url,verify=False)
    if response.status_code == 200:
        return json.loads(response.text)["main"]  # Extract relevant weather data
    else:
        raise Exception(f"Error fetching weather data: {response.status_code}")

# Fetch and process user data
user_data = get_user_data()
user_list = []
for user in user_data:
    if "address" in user and "geo" in user["address"]:
        user_list.append({
            "id": user["id"],
            "name": user["name"],
            "username": user["username"],
            "email": user["email"],
            "latitude": user["address"]["geo"]["lat"],
            "longitude": user["address"]["geo"]["lng"],
        })
user_df = pd.DataFrame(user_list)
user_df.rename(columns={"id":"customer_id","geo.lat": "latitude", "geo.lng": "longitude"}, inplace=True)

# Merge user data with sales data
merged_data = sales_data.merge(user_df, on="customer_id", how="left")

# Function to handle potential missing location data
def get_weather(row):
    try:
        latitude = row["latitude"]
        longitude = row["longitude"]
        weather_data = get_weather_data(latitude, longitude)
        return weather_data["temp"], weather_data["feels_like"], weather_data["temp_min"], weather_data["temp_max"]
    except Exception as e:
        print(f"Error fetching weather data for order ID {row['order_id']}: {e}")
        return None, None, None, None

# Add weather data using apply with error handling
merged_data[["temperature", "feels_like", "temp_min", "temp_max"]] = merged_data.apply(
    get_weather, axis=1, result_type="expand"
)

# Data manipulation and aggregations
total_sales_per_customer = merged_data.groupby("customer_id")["price"].sum()
avg_order_quantity_per_product = merged_data.groupby("product_id")["quantity"].mean()
top_selling_products = merged_data.nlargest(5, "price")["product_id"].unique()
top_spending_customers = merged_data.nlargest(5, "price")["customer_id"].unique()
merged_data["order_date"] = pd.to_datetime(merged_data["order_date"])
# Sales trends over time (replace with your preferred time-based grouping)
monthly_sales = merged_data.resample("M", on="order_date")["price"].sum()

# Analyze sales amount per weather condition (assuming temperature categories)
temperature_ranges = pd.cut(merged_data["temperature"], bins=[-10, 0, 10, 20, 30, 40])
avg_sales_per_temp_range = merged_data.groupby(temperature_ranges)["price"].mean()

# Bonus: Visualization (average sales per temperature range)
plt.figure(figsize=(10, 6))
avg_sales_per_temp_range.plot(kind="bar", color=plt.cm.viridis.colors)
plt.xlabel("Temperature Range (°C)")
plt.ylabel("Average Sales")
plt.title("Average Sales Amount by Temperature Range")
plt.xticks(rotation=0)
plt.tight_layout()
plt.show()  # Display the plot

# Function to connect to MySQL database
def connect_to_mysql():
    return pymysql.connect(host="172.30.16.1", user="root", password="Shubham1*", database="data_pipeline_schema")

# Function to store data in MySQL database
def store_data_in_mysql(connection, merged_data):
    cursor = connection.cursor()
    for index, row in merged_data.iterrows():
        # Insert customer data
        cursor.execute("""
        INSERT INTO Customers (customer_id, name, username, email)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE name=VALUES(name), username=VALUES(username), email=VALUES(email)
        """, (row["customer_id"], row["name"], row["username"], row["email"]))
        
       
         # Insert product data
        cursor.execute("""
        INSERT INTO Products (product_id, quantity)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE quantity=VALUES(quantity)
        """, (row["product_id"], row["quantity"]))
        
        # Insert sale data
        cursor.execute("""
        INSERT INTO Sales (customer_id, product_id, quantity, price, order_date)
        VALUES (%s, %s, %s, %s, %s)
        """, (row["customer_id"], row["product_id"], row["quantity"], row["price"], row["order_date"]))
        sale_id = cursor.lastrowid
        
        # Insert weather data
        cursor.execute("""
        INSERT INTO Weather (sale_id, temperature, feels_like, temp_min, temp_max)
        VALUES (%s, %s, %s, %s, %s)
        """, (sale_id, row["temperature"], row["feels_like"], row["temp_min"], row["temp_max"]))

    
    connection.commit()

# Main function to run the data pipeline
def main():
    # Connect to MySQL database
    connection = connect_to_mysql()

    # Store data in MySQL database
    store_data_in_mysql(connection, merged_data)

    # Close connection
    connection.close()

if __name__ == "__main__":
    main()
