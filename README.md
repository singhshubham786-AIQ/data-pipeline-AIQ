
Comprehensive Sales Data Pipeline

This project implements a comprehensive sales data pipeline for a retail company. The pipeline combines generated sales data with data from external sources, performs data transformations and aggregations, and stores the final dataset in a MySQL database. The aim is to enable analysis and derive insights into customer behavior and sales performance.

Table of Contents
Overview
Setup and Installation
Data Transformation Steps
Database Schema
Aggregations and Data Manipulation
Running the Data Pipeline
Dockerization
Contributing


Overview
The project consists of the following components:

Data Transformation: Fetches sales data from a CSV file, user data from the JSONPlaceholder API, and weather data from the OpenWeatherMap API. It then merges the data, performs necessary transformations, and adds weather information to each sale record.

Data Storage: Designs and creates a MySQL database schema to store the transformed data. Defines appropriate tables and data types, and writes logic to store the data into the database.
Aggregations and Analysis: Performs various data manipulations and aggregations to derive insights such as total sales per customer, average order quantity per product, top-selling products, and sales trends over time.
Visualization: Provides visualizations to present insights derived from the data, such as average sales per temperature range.

Setup and Installation
Clone Repository: Clone this repository to your local machine.
Install Dependencies: Make sure you have Python 3 installed on your system. Install the required Python libraries using pip:

pip install pandas requests matplotlib pymysql

Configure API Keys: Replace the placeholder API keys in the Python script (data_pipeline.py) with your actual API keys for JSONPlaceholder and OpenWeatherMap.

Provide Sales Data: Place your sales data CSV file in the project directory with the name "sales_data.csv".

Data Transformation Steps

Fetching Data: Sales data is loaded from a CSV file. User data is fetched from the JSONPlaceholder API, and weather data is fetched from the OpenWeatherMap API.

Merge Data: User data and sales data are merged based on the customer ID.

Handle Missing Data: If location data is missing for any user, those records are excluded from further processing.

Weather Data: Temperature and other weather parameters are extracted and associated with each sale.

Aggregations: Various aggregations are performed such as total sales per customer, average order quantity per product, etc.


Database Schema
The database schema consists of the following tables:

Customers Table: Stores customer information.
Products Table: Stores product information.
Sales Table: Stores sales data, including customer ID, product ID, quantity, price, and order date.
Weather Table: Stores weather data associated with each sale.
For detailed schema description, refer to the project documentation.

Aggregations and Data Manipulation

The following aggregations and data manipulation tasks are performed:

Total sales per customer
Average order quantity per product
Top selling products
Top spending customers
Sales trends over time
Average sales per temperature range
Running the Data Pipeline
To run the data pipeline, execute the Python script data_pipeline.py:


python data_pipeline.py

Ensure that you have configured the necessary API keys and provided the sales data CSV file.

Dockerization
The project can be dockerized for easy deployment. Refer to the Dockerfile in the repository for instructions on building and running the Docker image.