import requests  
import sqlite3  
import schedule  
import time  
import pandas as pd  
import numpy as np
import matplotlib.pyplot as plt
import logging  
from datetime import datetime, timedelta  
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from tkinter import filedialog  
import threading
from sklearn.linear_model import LinearRegression
from statsmodels.tsa.arima.model import ARIMA
import os

LICENSE_EXPIRATION_DATE = datetime.now() + timedelta(days=30)

def check_license():
    if datetime.now() > LICENSE_EXPIRATION_DATE:
        messagebox.showerror("License Expired", "Your license has expired. Please contact support.")
        exit()

logging.basicConfig(level=logging.INFO)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_DB_PATH = os.path.join(CURRENT_DIR, 'crypto_prices.db')  
COINMARKETCAP_API_KEY = "c233935f-ccc7-46dc-8016-6d9cef6c8553"  
BITCOIN_API_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest?symbol=BTC&convert=USDT"
COINGECKO_TETHER_DOMINANCE_URL = "https://api.coingecko.com/api/v3/global"

last_fetch_time = None
lock = threading.Lock()

def initialize_db():
    try:
        with sqlite3.connect(SQLITE_DB_PATH) as sqlite_conn:
            sqlite_cursor = sqlite_conn.cursor()
            sqlite_cursor.execute('''
                CREATE TABLE IF NOT EXISTS bitcoin_prices (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    price REAL NOT NULL,
                    price_status TEXT NOT NULL
                )
            ''')
            sqlite_conn.commit()
        logging.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logging.error(f"SQLite error during initialization: {e}")

def export_to_excel(log_text):
    try:
        file_path = filedialog.asksaveasfilename(defaultextension=".xlsx", 
                                                   filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                                                   title="Save Excel File")
        if not file_path:
            log_text.insert(tk.END, "Export canceled.\n")
            log_text.see(tk.END)
            return
        
        with sqlite3.connect(SQLITE_DB_PATH) as sqlite_conn:
            df = pd.read_sql_query("SELECT * FROM bitcoin_prices", sqlite_conn)

        if df.empty:
            log_text.insert(tk.END, "No data available to export.\n")
            log_text.see(tk.END)
            return

        df.to_excel(file_path, index=False)
        log_text.insert(tk.END, "Data exported to Excel successfully.\n")
        log_text.see(tk.END)
        logging.info("Data exported to Excel successfully.")
    except Exception as e:
        logging.error(f"Error exporting to Excel: {e}")
        log_text.insert(tk.END, f"Error exporting to Excel: {e}\n")
        log_text.see(tk.END)

def disable_buttons():
    for button in [forecast_linear_button, forecast_arima_button, clear_button, chart_button, current_price_button, export_button, settings_button]:
        if button.winfo_exists():
            button.config(state=tk.DISABLED)

def enable_buttons():
    for button in [forecast_linear_button, forecast_arima_button, clear_button, chart_button, current_price_button, export_button, settings_button]:
        if button.winfo_exists():
            button.config(state=tk.NORMAL)

def calculate_average_price():
    with sqlite3.connect(SQLITE_DB_PATH) as sqlite_conn:
        df = pd.read_sql_query("SELECT price FROM bitcoin_prices", sqlite_conn)
    if not df.empty:
        return round(df['price'].mean(), 2)
    return 0

def update_average_price_label():
    average_price = calculate_average_price()
    average_price_label.config(text=f"Average Bitcoin Price: {average_price} USDT")

def get_bitcoin_price(log_text, countdown_label):  
    global last_fetch_time, COINMARKETCAP_API_KEY, BITCOIN_API_URL  
    try:  
        disable_buttons()  
        current_time = datetime.now()
        
        if last_fetch_time is not None and (current_time - last_fetch_time).total_seconds() < 60:
            return  

        last_fetch_time = current_time  
        
        with lock:
            with sqlite3.connect(SQLITE_DB_PATH) as sqlite_conn:
                sqlite_cursor = sqlite_conn.cursor()  

                headers = {
                    'Accepts': 'application/json',
                    'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY,
                }
                response = requests.get(BITCOIN_API_URL, headers=headers, timeout=10)  
                response.raise_for_status()  
                data = response.json()  
                
                bitcoin_price = round(float(data['data']['BTC']['quote']['USDT']['price']), 2)
                current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M')
                last_price_data = sqlite_cursor.execute('SELECT price FROM bitcoin_prices ORDER BY id DESC LIMIT 1').fetchone()
                
                if last_price_data is not None:
                    last_price = last_price_data[0]
                    price_status = "Higher" if bitcoin_price > last_price else "Lower" if bitcoin_price < last_price else "Unchanged"
                else:
                    price_status = "Unchanged"

                sqlite_cursor.execute('INSERT INTO bitcoin_prices (timestamp, price, price_status) VALUES (?, ?, ?)', 
                                      (current_time_str, bitcoin_price, price_status))  
                sqlite_conn.commit()  

                logging.info(f"Bitcoin Price Received: {bitcoin_price} with status: {price_status}")
                log_text.insert(tk.END, f"Bitcoin price saved: {bitcoin_price}\n")
                log_text.see(tk.END)

                satoshi_price = round(bitcoin_price / 100000000, 8)
                if satoshi_label.winfo_exists():
                    satoshi_label.config(text=f"Satoshi Price: {satoshi_price} USDT")

                update_treeview()
                update_price_status_counts()
                update_average_price_label()  
                update_difference_label(bitcoin_price)  
                countdown(60, countdown_label)

    except requests.RequestException as e:  
        logging.error(f"Error fetching Bitcoin price: {e}")
        log_text.insert(tk.END, f"Error fetching Bitcoin price: {e}\n")
        log_text.see(tk.END)
    except sqlite3.Error as e:  
        logging.error(f"SQLite error: {e}")
        log_text.insert(tk.END, f"SQLite error: {e}\n")
        log_text.see(tk.END)
    except Exception as e:  
        logging.error(f"Error saving to database: {e}")
        log_text.insert(tk.END, f"Error saving to database: {e}\n")
        log_text.see(tk.END)
    finally:
        enable_buttons()  

def get_tether_dominance(log_text):
    try:
        response = requests.get(COINGECKO_TETHER_DOMINANCE_URL)
        
        if response.status_code == 200:
            data = response.json()
            tether_dominance = data['data']['market_cap_percentage']['usdt']
            tether_dominance_label.config(text=f"Tether Dominance: {tether_dominance:.2f}%")
            
            if tether_dominance < 4:
                tether_dominance_label.config(foreground="brown")
            else:
                tether_dominance_label.config(foreground="blue")
                
            logging.info(f"Tether Dominance Received: {tether_dominance}%")
        else:
            log_text.insert(tk.END, "Failed to retrieve Tether dominance data.\n")
            tether_dominance_label.config(text="Tether Dominance: 0.00%")
            logging.error(f"Error fetching Tether dominance: {response.status_code}")

    except requests.RequestException as e:
        logging.error(f"Error fetching Tether dominance: {e}")
        log_text.insert(tk.END, f"Error fetching Tether dominance: {e}\n")
        log_text.see(tk.END)

def get_bitcoin_dominance(log_text):
    try:
        response = requests.get(COINGECKO_TETHER_DOMINANCE_URL)
        
        if response.status_code == 200:
            data = response.json()
            bitcoin_dominance = data['data']['market_cap_percentage']['btc']
            bitcoin_dominance_label.config(text=f"Bitcoin Dominance: {bitcoin_dominance:.2f}%")
            
            if bitcoin_dominance < 40:
                bitcoin_dominance_label.config(foreground="brown")
            else:
                bitcoin_dominance_label.config(foreground="blue")
                
            logging.info(f"Bitcoin Dominance Received: {bitcoin_dominance}%")
        else:
            log_text.insert(tk.END, "Failed to retrieve Bitcoin dominance data.\n")
            bitcoin_dominance_label.config(text="Bitcoin Dominance: 0.00%")
            logging.error(f"Error fetching Bitcoin dominance: {response.status_code}")

    except requests.RequestException as e:
        logging.error(f"Error fetching Bitcoin dominance: {e}")
        log_text.insert(tk.END, f"Error fetching Bitcoin dominance: {e}\n")
        log_text.see(tk.END)

def update_difference_label(current_price):
    average_price = calculate_average_price()
    difference = current_price - average_price
    difference_label.config(text=f"Price Difference: {difference:.2f} USDT")

    if difference > 0:
        difference_label.config(foreground="green")
    else:
        difference_label.config(foreground="red")

def update_price_status_counts():
    with sqlite3.connect(SQLITE_DB_PATH) as sqlite_conn:
        df_counts = pd.read_sql_query("SELECT price_status, COUNT(*) as count FROM bitcoin_prices GROUP BY price_status", sqlite_conn)

    counts = {'Higher': 0, 'Lower': 0, 'Unchanged': 0}
    for index, row in df_counts.iterrows():
        counts[row['price_status']] = row['count']

    for widget in status_frame.winfo_children():
        widget.destroy()

    for status, count in counts.items():
        label = ttk.Label(status_frame, text=f"{status}: {count}")
        label.pack(side=tk.LEFT, padx=5)

def countdown(remaining, countdown_label):
    if remaining > 0:
        countdown_label.config(text=f"Next update in: {remaining} seconds")
        countdown_label.after(1000, countdown, remaining - 1, countdown_label)
    else:
        countdown_label.config(text="Updating...")
        get_bitcoin_price(log_text, countdown_label)
        get_tether_dominance(log_text)
        get_bitcoin_dominance(log_text)

def clear_database(log_text):
    if messagebox.askyesno("Confirm Deletion", "Are you sure you want to clear all data from the database? This action cannot be undone."):
        try:
            with sqlite3.connect(SQLITE_DB_PATH) as sqlite_conn:
                sqlite_cursor = sqlite_conn.cursor()
                sqlite_cursor.execute('DELETE FROM bitcoin_prices')
                sqlite_conn.commit()

            logging.info("Database cleared successfully.")
            log_text.insert(tk.END, "Database cleared successfully.\n")
            log_text.see(tk.END)

            update_treeview()

        except sqlite3.Error as e:
            logging.error(f"SQLite error while clearing database: {e}")
            log_text.insert(tk.END, f"SQLite error while clearing database: {e}\n")
            log_text.see(tk.END)
        except Exception as e:
            logging.error(f"Error while clearing database: {e}")
            log_text.insert(tk.END, f"Error while clearing database: {e}\n")
            log_text.see(tk.END)

def forecast_prices_linear(log_text):
    # اخطار به کاربر
    messagebox.showwarning("Warning", "Warning: Any financial losses or damages resulting from the use of this prediction feature are your own responsibility.")
    
    user_input_value = float(user_input_entry.get())
    
    try:
        with sqlite3.connect(SQLITE_DB_PATH) as sqlite_conn:
            data = pd.read_sql_query("SELECT * FROM bitcoin_prices", sqlite_conn)

        data['timestamp'] = pd.to_datetime(data['timestamp'])
        data.set_index('timestamp', inplace=True)
        data = data.asfreq('min')
        data['price'].interpolate(method='linear', inplace=True)

        data['time_index'] = np.arange(len(data))  
        X = data['time_index'].values.reshape(-1, 1)  
        y = data['price'].values  

        model = LinearRegression()
        model.fit(X, y)

        future_time_index = np.arange(len(data), len(data) + 30).reshape(-1, 1)
        predictions_linear = model.predict(future_time_index)
        predictions_linear += user_input_value

        plt.figure(figsize=(12, 6))
        plt.plot(data.index, data['price'], label='Actual Data', color='blue')
        plt.plot(data.index[-1] + pd.to_timedelta(np.arange(1, 31), unit='m'), predictions_linear, label='Linear Regression Forecast', color='red')
        plt.title('Price Forecast using Linear Regression for Next Minutes')
        plt.xlabel('Time')
        plt.ylabel('Price')
        plt.legend()
        plt.show()

        logging.info("Linear Regression forecasting completed successfully.")
        log_text.insert(tk.END, "Linear Regression forecasting completed successfully.\n")
        log_text.see(tk.END)

    except Exception as e:
        logging.error(f"Error during Linear Regression forecasting: {e}")
        log_text.insert(tk.END, f"Error during Linear Regression forecasting: {e}\n")
        log_text.see(tk.END)

def forecast_prices_arima(log_text):
    # اخطار به کاربر
    messagebox.showwarning("Warning", "Warning: Any financial losses or damages resulting from the use of this prediction feature are your own responsibility.")
    
    user_input_value = float(user_input_entry.get())
    
    try:
        with sqlite3.connect(SQLITE_DB_PATH) as sqlite_conn:
            data = pd.read_sql_query("SELECT * FROM bitcoin_prices", sqlite_conn)

        data['timestamp'] = pd.to_datetime(data['timestamp'])
        data.set_index('timestamp', inplace=True)
        data = data.asfreq('min')
        data['price'].interpolate(method='linear', inplace=True)

        model_arima = ARIMA(data['price'], order=(5, 1, 0))
        model_fit = model_arima.fit()

        forecast_arima = model_fit.forecast(steps=30)
        forecast_arima += user_input_value

        plt.figure(figsize=(12, 6))
        plt.plot(data.index, data['price'], label='Actual Data', color='blue')
        plt.plot(data.index[-1] + pd.to_timedelta(np.arange(1, 31), unit='m'), forecast_arima, label='ARIMA Forecast', color='green')
        plt.title('Price Forecast using ARIMA Model for Next Minutes')
        plt.xlabel('Time')
        plt.ylabel('Price')
        plt.legend()
        plt.show()

        logging.info("ARIMA forecasting completed successfully.")
        log_text.insert(tk.END, "ARIMA forecasting completed successfully.\n")
        log_text.see(tk.END)

    except Exception as e:
        logging.error(f"Error during ARIMA forecasting: {e}")
        log_text.insert(tk.END, f"Error during ARIMA forecasting: {e}\n")
        log_text.see(tk.END)

def show_current_price_and_chart(log_text):
    try:
        headers = {
            'Accepts': 'application/json',
            'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY,
        }
        response = requests.get(BITCOIN_API_URL, headers=headers, timeout=10)  
        response.raise_for_status()  
        data = response.json()  
        
        current_price = float(data['data']['BTC']['quote']['USDT']['price'])  
        messagebox.showinfo("Current Bitcoin Price", f"The current price of Bitcoin is: {current_price} USDT")
        
        with sqlite3.connect(SQLITE_DB_PATH) as sqlite_conn:
            historical_data = pd.read_sql_query("SELECT * FROM bitcoin_prices", sqlite_conn)

        historical_data['timestamp'] = pd.to_datetime(historical_data['timestamp'])
        plt.figure(figsize=(12, 6))
        plt.plot(historical_data['timestamp'], historical_data['price'], label='Historical Price', color='blue')
        plt.title('Historical Bitcoin Prices')
        plt.xlabel('Time')
        plt.ylabel('Price (in Bitcoin)')
        plt.legend()
        plt.show()

    except requests.RequestException as e:
        logging.error(f"Error fetching current Bitcoin price: {e}")
        log_text.insert(tk.END, f"Error fetching current Bitcoin price: {e}\n")
        log_text.see(tk.END)

def plot_chart(log_text):
    try:
        with sqlite3.connect(SQLITE_DB_PATH) as sqlite_conn:
            df_chart = pd.read_sql_query("SELECT * FROM bitcoin_prices", sqlite_conn)

        if df_chart.empty:
            log_text.insert(tk.END, "No data available to plot.\n")
            log_text.see(tk.END)
            return

        df_chart['timestamp'] = pd.to_datetime(df_chart['timestamp'])
        status_counts = df_chart['price_status'].value_counts()
        plt.figure(figsize=(10, 5))
        plt.bar(status_counts.index, status_counts.values, color=['green' if x == 'Higher' else 'red' if x == 'Lower' else 'gray' for x in status_counts.index])
        plt.title('Price Status Counts')
        plt.xlabel('Price Status')
        plt.ylabel('Count')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

        logging.info("Chart plotted successfully.")
        log_text.insert(tk.END, "Chart plotted successfully.\n")
        log_text.see(tk.END)

    except Exception as e:
        logging.error(f"Error plotting chart: {e}")
        log_text.insert(tk.END, f"Error plotting chart: {e}\n")
        log_text.see(tk.END)

def update_treeview():
    for row in tree.get_children():
        tree.delete(row)

    with sqlite3.connect(SQLITE_DB_PATH) as sqlite_conn:
        df_db = pd.read_sql_query("SELECT * FROM bitcoin_prices ORDER BY id DESC", sqlite_conn)

    for index, row in df_db.iterrows():
        tree.insert("", "end", values=(row['id'], row['timestamp'], row['price'], row['price_status']))

def schedule_task(log_text):
    schedule.every(1).minutes.do(get_bitcoin_price, log_text=log_text, countdown_label=countdown_label)
    schedule.every(1).minutes.do(get_tether_dominance, log_text=log_text)
    schedule.every(1).minutes.do(get_bitcoin_dominance, log_text=log_text)

    def run_schedule():
        while True:  
            schedule.run_pending()  
            time.sleep(1)

    threading.Thread(target=run_schedule, daemon=True).start()

def open_settings():
    settings_window = tk.Toplevel()
    settings_window.title("Settings")
    settings_window.geometry("300x200")

    url_label = ttk.Label(settings_window, text="API URL:")
    url_label.pack(pady=5)
    url_entry = ttk.Entry(settings_window, width=40)
    url_entry.insert(0, BITCOIN_API_URL)
    url_entry.pack(pady=5)

    api_label = ttk.Label(settings_window, text="API Key:")
    api_label.pack(pady=5)
    api_entry = ttk.Entry(settings_window, width=40)
    api_entry.insert(0, COINMARKETCAP_API_KEY)
    api_entry.pack(pady=5)

    def save_settings():
        global BITCOIN_API_URL, COINMARKETCAP_API_KEY
        new_url = url_entry.get()
        new_api_key = api_entry.get()

        if new_url != BITCOIN_API_URL or new_api_key != COINMARKETCAP_API_KEY:
            if messagebox.askyesno("Confirm", "Changing settings will clear the database. Do you want to proceed?"):
                clear_database(log_text)

        BITCOIN_API_URL = new_url
        COINMARKETCAP_API_KEY = new_api_key
        settings_window.destroy()
        messagebox.showinfo("Settings", "Settings saved successfully!")

    save_button = ttk.Button(settings_window, text="Save", command=save_settings)
    save_button.pack(pady=20)

def create_gui():
    global tree, countdown_label, log_text, satoshi_label, status_frame, user_input_entry, average_price_label, difference_label
    global forecast_linear_button, forecast_arima_button, clear_button, chart_button, current_price_button, export_button, settings_button, tether_dominance_label, bitcoin_dominance_label

    root = tk.Tk()
    root.title("Bitcoin Forecast Tracker")  
    root.geometry("840x815")  
    root.resizable(False, False)  

    frame = ttk.Frame(root, padding="10")
    frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    countdown_label = ttk.Label(frame, text="Next update in: 60 seconds", font=("Helvetica", 12))
    countdown_label.grid(row=0, column=0, padx=10, pady=10, columnspan=2)  

    satoshi_label = ttk.Label(frame, text="Satoshi Price: 0 USDT", font=("Helvetica", 12))
    satoshi_label.grid(row=1, column=0, padx=10, pady=10, columnspan=2)

    average_price_label = ttk.Label(frame, text="Average Bitcoin Price: 0 USDT", font=("Helvetica", 12))
    average_price_label.grid(row=2, column=0, padx=10, pady=10, columnspan=2)

    difference_label = ttk.Label(frame, text="Price Difference: 0.00 USDT", font=("Helvetica", 12))
    difference_label.grid(row=3, column=0, padx=10, pady=10, columnspan=2)

    tether_dominance_label = ttk.Label(frame, text="Tether Dominance: 0.00%", font=("Helvetica", 12))
    tether_dominance_label.grid(row=4, column=0, padx=10, pady=10, columnspan=2)

    bitcoin_dominance_label = ttk.Label(frame, text="Bitcoin Dominance: 0.00%", font=("Helvetica", 12))
    bitcoin_dominance_label.grid(row=5, column=0, padx=10, pady=10, columnspan=2)

    status_frame = ttk.Frame(frame)
    status_frame.grid(row=6, column=0, padx=10, pady=5, columnspan=2)

    user_input_label = ttk.Label(frame, text="Enter prediction value:")
    user_input_label.grid(row=7, column=0, padx=10, pady=5)

    user_input_entry = ttk.Entry(frame)
    user_input_entry.grid(row=7, column=1, padx=10, pady=5)
    user_input_entry.insert(0, "1440")

    forecast_linear_button = ttk.Button(frame, text="Forecast with Linear Regression", command=lambda: forecast_prices_linear(log_text))
    forecast_linear_button.grid(row=8, column=0, padx=10, pady=5)

    forecast_arima_button = ttk.Button(frame, text="Forecast with ARIMA", command=lambda: forecast_prices_arima(log_text))
    forecast_arima_button.grid(row=8, column=1, padx=10, pady=5)

    clear_button = ttk.Button(frame, text="Clear Database", command=lambda: clear_database(log_text))
    clear_button.grid(row=9, column=0, padx=10, pady=5)

    chart_button = ttk.Button(frame, text="Counter", command=lambda: plot_chart(log_text))
    chart_button.grid(row=9, column=1, padx=10, pady=5)

    current_price_button = ttk.Button(frame, text="Show Current Price", command=lambda: show_current_price_and_chart(log_text))
    current_price_button.grid(row=10, column=0, padx=10, pady=5)

    export_button = ttk.Button(frame, text="Export to Excel", command=lambda: export_to_excel(log_text))
    export_button.grid(row=10, column=1, padx=10, pady=5)

    settings_button = ttk.Button(frame, text="Settings", command=open_settings)
    settings_button.grid(row=11, column=0, padx=10, pady=5, columnspan=2)

    log_text = tk.Text(frame, height=3, width=50)  
    log_text.grid(row=12, column=0, columnspan=2, padx=10, pady=10)

    tree = ttk.Treeview(frame, columns=("ID", "Timestamp", "Price", "Price Status"), show='headings')
    tree.heading("ID", text="ID")
    tree.heading("Timestamp", text="Timestamp")
    tree.heading("Price", text="Price")
    tree.heading("Price Status", text="Price Status")
    tree.grid(row=13, column=0, columnspan=2, padx=10, pady=10)

    contact_label = ttk.Label(frame, text="Contact us on WhatsApp (Rev:6.0.1): +98-936-358-4718", foreground="blue")
    contact_label.grid(row=14, column=0, columnspan=2, padx=10, pady=10)

    update_treeview()
    schedule_task(log_text)
    get_bitcoin_price(log_text, countdown_label)
    get_tether_dominance(log_text)
    get_bitcoin_dominance(log_text)

    root.mainloop()

if __name__ == "__main__":  
    check_license()  
    initialize_db()  
    create_gui()  

    try:  
        while True:  
            schedule.run_pending()  
            time.sleep(1)  
    except KeyboardInterrupt:  
        logging.info("Stopping the scheduler...")  
    finally:  
        logging.info("Database connection closed.")
