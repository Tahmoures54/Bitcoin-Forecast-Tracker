# Bitcoin-Forecast-Tracker

A Python-based project for real-time Bitcoin price prediction and trading assistance. This application features real-time data fetching, historical data storage, visualizations, Excel export, and predictive analytics using Linear Regression and ARIMA models. It includes a user-friendly GUI built with tkinter.

## Introduction

This project aims to predict the price of Bitcoin using various machine learning models and provide valuable services to traders. The system fetches real-time Bitcoin prices, stores them in a local SQLite database, and offers features like data visualization, exporting to Excel, and trading signals.

## Features
- **Real-time Bitcoin Price Fetching**: Retrieve real-time Bitcoin prices from the CoinMarketCap API.
- **Price Status Tracking**: Track whether the current price is higher, lower, or unchanged compared to the previous value.
- **Database Storage**: Store historical Bitcoin prices in a SQLite database.
- **Data Export**: Export the stored data to an Excel file for further analysis.
- **Average Price Calculation**: Calculate and display the average Bitcoin price.
- **Linear Regression Prediction**: Implement Linear Regression to predict future prices.
- **ARIMA Model Prediction**: Utilize ARIMA model for advanced time-series forecasting.
- **Bitcoin and Tether Dominance Tracking**: Fetch and display the dominance of Bitcoin and Tether in the cryptocurrency market.
- **Price Difference Calculation**: Calculate and display the difference between the current Bitcoin price and the average price.
- **Clear Database**: Clear all data from the database with user confirmation.
- **Current Price Display and Historical Chart**: Display the current Bitcoin price and plot historical prices.
- **Plot Chart for Price Status**: Visualize the count of price statuses ("Higher", "Lower", "Unchanged").
- **TreeView Update**: Dynamically update the TreeView with the latest Bitcoin price data.
- **Scheduled Tasks**: Automate data fetching and processing at regular intervals.
- **Settings Window**: Provide a settings window to update API URL and key.

## Technologies Used
- **Programming Language**: Python
- **Data Handling**: pandas, numpy, sqlite3
- **Visualization**: matplotlib
- **Machine Learning**: scikit-learn, statsmodels
- **API Integration**: requests
- **User Interface**: tkinter
- **Logging**: logging
- **Threading**: threading
- **Scheduling**: schedule

## Setup and Installation

### Prerequisites
Make sure you have Python installed on your machine. You can download it from [python.org](https://www.python.org/downloads/).

### Installation Steps
1. Clone the repository:
   ```sh
   git clone https://github.com/Tahmoures54/Bitcoin-Forecast-Tracker.git
   
2. Navigate to the project directory:
  ```sh
   cd Bitcoin-Forecast-Tracker

3. Install the required dependencies:
  ```sh
   pip install -r requirements.txt

## Usage
1. Initialize the database:
  ```sh
   python initialize_db.py

2. Run the main application:
  ```sh
   python main.py

  
## Results
The application provides real-time price updates, historical data storage, and predictive analytics through interactive visualizations and machine learning models. Exported data can be further analyzed in Excel.

## Contributions
Feel free to fork the repository and submit pull requests. Any contributions are welcome!

## License
This project is licensed under the MIT License.

## Contact
For software orders or assistance, please contact me on WhatsApp: +989363584718. 
