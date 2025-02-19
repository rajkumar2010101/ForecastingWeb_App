from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
import os
import random
from datetime import datetime, timedelta
import traceback
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

df = None

def preprocess_data(file_path):
    global df
    try:
        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path)
        elif file_path.endswith((".xls", ".xlsx")):
            df = pd.read_excel(file_path)
        else:
            return "Unsupported file format. Please upload a CSV or Excel file."

        # Validate required columns
        required_columns = ["Year", "Week", "Mon", "Tue", "Wed", "Thu", "Fri", "Total Offered"]
        if not all(col in df.columns for col in required_columns):
            return f"Invalid data format! Required columns: {', '.join(required_columns)}"

        # Convert Year and Week into a proper date (Monday of the week)
        df['Date'] = pd.to_datetime(
            df['Year'].astype(str) + '-W' + df['Week'].astype(str) + '-1',
            format='%Y-W%W-%w',
            errors='coerce'
        )
        if df['Date'].isnull().any():
            return "Invalid Year-Week combination. Please check your data."

        df.dropna(subset=['Date'], inplace=True)
        df.sort_values('Date', inplace=True)
        df.set_index('Date', inplace=True)

        if df.index.duplicated().any():
            return "Duplicate weeks found in the dataset."

        return True
    except Exception as e:
        print(f"Error in preprocessing: {e}")
        traceback.print_exc()
        return str(e)

def fit_arima_model(series, order=(1, 1, 1)):
    model = ARIMA(series, order=order)
    return model.fit()

def forecast_daily_volumes(df, model_type='ARIMA'):
    try:
        forecasts = {}
        accuracy = {}
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']

        for day in days:
            series = df[day]

            if model_type == 'ARIMA':
                model = fit_arima_model(series)
                forecast = model.forecast(steps=1)
                train_pred = model.fittedvalues
            elif model_type == 'RandomForecast':
                # Randomly sample a value from the historical data for forecasting
                forecast = random.choice(series.values)
                train_pred = series.values  # Use the actual series as the 'prediction' for error calculation
            elif model_type == 'HoltWinters':
                model = ExponentialSmoothing(series, trend='add', seasonal='add', seasonal_periods=2)
                model_fit = model.fit()
                forecast = model_fit.forecast(steps=1)
                train_pred = model_fit.fittedvalues

            forecasts[day] = int(np.round(forecast))  # Round and store forecast

            # Calculate MAPE for accuracy (Mean Absolute Percentage Error)
            mape = np.mean(np.abs((series[1:] - train_pred[1:]) / series[1:])) * 100
            accuracy[day] = round(mape, 2)

        # Get the next week's date range
        last_date = df.index[-1]
        next_week_dates = [last_date + timedelta(days=i) for i in range(1, 6)]  # Monday to Friday

        print(f"Forecasts: {forecasts}")  # Debugging
        print(f"Accuracy: {accuracy}")    # Debugging
        print(f"Next Week Dates: {next_week_dates}")  # Debugging

        return {
            'forecasts': forecasts,
            'accuracy': accuracy,
            'next_week_dates': [date.strftime('%Y-%m-%d') for date in next_week_dates]
        }
    except Exception as e:
        print(f"Forecasting error: {e}")
        traceback.print_exc()
        return None
    
@app.route('/')
def home():
    return render_template("index.html")

@app.route('/about')
def about():
    return render_template("about.html")


@app.route('/upload', methods=['POST'])
def upload_file():
    global df
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"})

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"})

    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        result = preprocess_data(file_path)
        if result is not True:
            return jsonify({"error": result})

        years = df['Year'].unique()
        years.sort()
        year_range = f"{years[0]} to {years[-1]}" if len(years) > 1 else f"{years[0]}"
        num_weeks = len(df)

        return jsonify({
            "message": f"File processed successfully! Contains {num_weeks} weeks from {year_range}.",
            "years": years.tolist(),
            "weeks": num_weeks
        })
    except Exception as e:
        return jsonify({"error": f"Processing error: {str(e)}"})

@app.route('/predict', methods=['POST'])
def predict():
    global df
    if df is None:
        return jsonify({"error": "Please upload a file first!"})

    try:
        data = request.get_json()
        model_type = data.get('model', 'ARIMA')
        result = forecast_daily_volumes(df, model_type)
        if not result:
            return jsonify({"error": "Error generating forecast"})

        return jsonify({
            "forecasts": result['forecasts'],
            "accuracy": result['accuracy'],
            "next_week_dates": result['next_week_dates']
        })
    except Exception as e:
        return jsonify({"error": f"Prediction error: {str(e)}"})

if __name__ == '__main__':
    app.run(debug=True)
