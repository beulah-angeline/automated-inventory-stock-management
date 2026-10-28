# Automated Inventory Stock Management Alert System

A beginner-friendly Flask + SQLite web application for managing stock, recording stock-in/stock-out transactions, identifying low/out-of-stock items, and exporting CSV reports.

## Requirements
- Python 3.10 or newer
- Internet connection for the first-time Flask installation

## Run on Windows
1. Extract the ZIP file.
2. Open the extracted `inventory_stock_alert` folder.
3. Double-click `run_windows.bat`.
4. Wait for Flask to start, then open http://127.0.0.1:5000 in your browser.

Alternative (terminal):
```bash
python -m pip install -r requirements.txt
python app.py
```

The database `inventory.db` is created automatically when you start the app. Sample products are inserted on the first run.

## Features
- Dashboard with product count, low-stock count, out-of-stock count and stock value
- Add, edit, delete and search products
- Stock In and Stock Out transactions with validation
- Prevents stock from becoming negative
- Automatic In Stock / Low Stock / Out of Stock status
- Product and transaction CSV exports
- Recent transaction history
- SQLite persistence

## Project structure
```text
inventory_stock_alert/
  app.py
  requirements.txt
  run_windows.bat
  README.md
  templates/
  static/
```

## Demo notes
This is an educational demo. Change the Flask secret key and add login/role controls before using it for real business data. The application has not been tested on every computer configuration.
