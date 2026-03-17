"""
ReplenishIQ Forecasting Engine
Implements 3 forecasting models for demand prediction:
1. Moving Average
2. Exponential Smoothing
3. Linear Regression with seasonality

Each model predicts future demand to optimize replenishment parameters.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
import os
import warnings
warnings.filterwarnings('ignore')

def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_sales_data():
    """Load sales data from CSV."""
    project_root = get_project_root()
    sales_path = os.path.join(project_root, 'data', 'processed', 'fact_sales.csv')
    df = pd.read_csv(sales_path)
    df['date'] = pd.to_datetime(df['date'])
    return df

def prepare_sku_timeseries(sales_df, sku_id):
    """Prepare daily time series for a specific SKU."""
    sku_sales = sales_df[sales_df['sku_id'] == sku_id].copy()
    
    # Create complete date range
    date_range = pd.date_range(start=sales_df['date'].min(), end=sales_df['date'].max(), freq='D')
    
    # Aggregate by date and reindex to fill missing dates with 0
    daily_sales = sku_sales.groupby('date')['units_sold'].sum().reindex(date_range, fill_value=0)
    daily_sales.index.name = 'date'
    
    return daily_sales.reset_index().rename(columns={0: 'units_sold'}) if isinstance(daily_sales, pd.Series) else daily_sales


# =============================================================================
# MODEL 1: MOVING AVERAGE
# =============================================================================

class MovingAverageModel:
    """
    Simple Moving Average forecasting.
    Predicts future demand as the average of the last N days.
    
    Best for: Stable demand with no strong trend or seasonality.
    """
    
    def __init__(self, window=7):
        """
        Args:
            window: Number of days to average (default 7 = weekly average)
        """
        self.window = window
        self.last_values = None
        
    def fit(self, series):
        """
        Fit the model by storing the last 'window' values.
        
        Args:
            series: pandas Series with daily demand values
        """
        self.last_values = series.tail(self.window).values
        return self
    
    def predict(self, horizon=30):
        """
        Predict future demand.
        
        Args:
            horizon: Number of days to forecast
            
        Returns:
            numpy array of predictions
        """
        if self.last_values is None:
            raise ValueError("Model not fitted. Call fit() first.")
        
        predictions = []
        rolling_window = list(self.last_values)
        
        for _ in range(horizon):
            # Predict as average of window
            pred = np.mean(rolling_window)
            predictions.append(pred)
            
            # Update rolling window
            rolling_window.pop(0)
            rolling_window.append(pred)
        
        return np.array(predictions)
    
    def __repr__(self):
        return f"MovingAverageModel(window={self.window})"


# =============================================================================
# MODEL 2: EXPONENTIAL SMOOTHING
# =============================================================================

class ExponentialSmoothingModel:
    """
    Simple Exponential Smoothing (SES) forecasting.
    Gives more weight to recent observations, less to older ones.
    
    Formula: forecast = alpha * actual + (1 - alpha) * previous_forecast
    
    Best for: Data with no clear trend, but recent values matter more.
    """
    
    def __init__(self, alpha=0.3):
        """
        Args:
            alpha: Smoothing factor (0 to 1)
                   - Higher alpha = more weight on recent data
                   - Lower alpha = smoother, more stable forecasts
        """
        self.alpha = alpha
        self.last_smoothed = None
        
    def fit(self, series):
        """
        Fit the model by calculating smoothed values.
        
        Args:
            series: pandas Series with daily demand values
        """
        values = series.values
        smoothed = values[0]  # Initialize with first value
        
        for val in values[1:]:
            smoothed = self.alpha * val + (1 - self.alpha) * smoothed
        
        self.last_smoothed = smoothed
        return self
    
    def predict(self, horizon=30):
        """
        Predict future demand.
        For simple exponential smoothing, all future predictions are the same.
        
        Args:
            horizon: Number of days to forecast
            
        Returns:
            numpy array of predictions
        """
        if self.last_smoothed is None:
            raise ValueError("Model not fitted. Call fit() first.")
        
        # SES predicts a flat line into the future
        return np.full(horizon, self.last_smoothed)
    
    def __repr__(self):
        return f"ExponentialSmoothingModel(alpha={self.alpha})"


# =============================================================================
# MODEL 3: LINEAR REGRESSION WITH SEASONALITY
# =============================================================================

class LinearRegressionModel:
    """
    Linear Regression with seasonal features.
    Captures trend and seasonality patterns.
    
    Features used:
    - Day of week (0-6)
    - Month (1-12)
    - Quarter (1-4)
    - Trend (days since start)
    
    Best for: Data with clear trends and/or seasonal patterns.
    """
    
    def __init__(self):
        self.model = LinearRegression()
        self.scaler = StandardScaler()
        self.is_fitted = False
        self.start_date = None
        
    def _create_features(self, dates):
        """Create feature matrix from dates."""
        df = pd.DataFrame({'date': dates})
        df['day_of_week'] = df['date'].dt.dayofweek
        df['month'] = df['date'].dt.month
        df['quarter'] = df['date'].dt.quarter
        df['day_of_year'] = df['date'].dt.dayofyear
        df['trend'] = (df['date'] - self.start_date).dt.days
        
        # Cyclical encoding for day of week and month
        df['dow_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['dow_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
        df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
        df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
        
        feature_cols = ['trend', 'dow_sin', 'dow_cos', 'month_sin', 'month_cos', 'quarter']
        return df[feature_cols].values
    
    def fit(self, series, dates):
        """
        Fit the model.
        
        Args:
            series: pandas Series with daily demand values
            dates: pandas Series with corresponding dates
        """
        self.start_date = dates.min()
        X = self._create_features(dates)
        X_scaled = self.scaler.fit_transform(X)
        
        y = series.values
        self.model.fit(X_scaled, y)
        self.is_fitted = True
        self.last_date = dates.max()
        return self
    
    def predict(self, horizon=30):
        """
        Predict future demand.
        
        Args:
            horizon: Number of days to forecast
            
        Returns:
            numpy array of predictions
        """
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call fit() first.")
        
        future_dates = pd.date_range(start=self.last_date + timedelta(days=1), periods=horizon, freq='D')
        X_future = self._create_features(future_dates)
        X_scaled = self.scaler.transform(X_future)
        
        predictions = self.model.predict(X_scaled)
        # Ensure non-negative predictions
        predictions = np.maximum(predictions, 0)
        
        return predictions
    
    def __repr__(self):
        return "LinearRegressionModel(with_seasonality=True)"


# =============================================================================
# FORECAST ENGINE - COMBINES ALL MODELS
# =============================================================================

class ForecastEngine:
    """
    Main forecasting engine that runs all models and selects the best one.
    """
    
    def __init__(self):
        self.models = {
            'moving_average_7': MovingAverageModel(window=7),
            'moving_average_14': MovingAverageModel(window=14),
            'moving_average_30': MovingAverageModel(window=30),
            'exp_smoothing_0.1': ExponentialSmoothingModel(alpha=0.1),
            'exp_smoothing_0.3': ExponentialSmoothingModel(alpha=0.3),
            'exp_smoothing_0.5': ExponentialSmoothingModel(alpha=0.5),
            'linear_regression': LinearRegressionModel()
        }
        self.best_model = None
        self.best_model_name = None
        self.metrics = {}
        
    def evaluate_models(self, series, dates, test_size=30):
        """
        Evaluate all models using train/test split.
        
        Args:
            series: Full time series
            dates: Corresponding dates
            test_size: Number of days to hold out for testing
        """
        train_series = series[:-test_size]
        train_dates = dates[:-test_size]
        test_series = series[-test_size:]
        
        results = {}
        
        for name, model in self.models.items():
            try:
                if isinstance(model, LinearRegressionModel):
                    model.fit(train_series, train_dates)
                else:
                    model.fit(train_series)
                
                predictions = model.predict(horizon=test_size)
                
                mae = mean_absolute_error(test_series, predictions)
                rmse = np.sqrt(mean_squared_error(test_series, predictions))
                
                results[name] = {
                    'mae': mae,
                    'rmse': rmse,
                    'predictions': predictions
                }
            except Exception as e:
                results[name] = {'error': str(e)}
        
        self.metrics = results
        
        # Select best model based on MAE
        valid_results = {k: v for k, v in results.items() if 'mae' in v}
        if valid_results:
            self.best_model_name = min(valid_results, key=lambda x: valid_results[x]['mae'])
            self.best_model = self.models[self.best_model_name]
        
        return results
    
    def forecast(self, series, dates, horizon=30):
        """
        Generate forecast using the best model.
        
        Args:
            series: Full time series
            dates: Corresponding dates
            horizon: Days to forecast
            
        Returns:
            dict with predictions and model info
        """
        # First evaluate to find best model
        self.evaluate_models(series, dates)
        
        # Refit best model on full data
        if isinstance(self.best_model, LinearRegressionModel):
            self.best_model.fit(series, dates)
        else:
            self.best_model.fit(series)
        
        predictions = self.best_model.predict(horizon=horizon)
        
        # Generate future dates
        last_date = dates.max()
        future_dates = pd.date_range(start=last_date + timedelta(days=1), periods=horizon, freq='D')
        
        return {
            'model': self.best_model_name,
            'predictions': predictions,
            'dates': future_dates,
            'metrics': self.metrics
        }


# =============================================================================
# MAIN FUNCTION - RUN FORECASTS FOR ALL SKUS
# =============================================================================

def run_forecasts(sku_list=None, horizon=30, output_file='forecasts.csv'):
    """
    Run forecasts for multiple SKUs and save results.
    
    Args:
        sku_list: List of SKU IDs to forecast (None = all SKUs)
        horizon: Days to forecast
        output_file: Output filename
    """
    print("=" * 60)
    print("ReplenishIQ Forecasting Engine")
    print("=" * 60)
    
    # Load data
    print("\nLoading sales data...")
    sales_df = load_sales_data()
    
    if sku_list is None:
        sku_list = sales_df['sku_id'].unique()[:50]  # Limit to 50 for demo
    
    print(f"Forecasting {len(sku_list)} SKUs for {horizon} days ahead...")
    
    results = []
    engine = ForecastEngine()
    
    for i, sku_id in enumerate(sku_list):
        if (i + 1) % 10 == 0:
            print(f"  Processing SKU {i + 1}/{len(sku_list)}...")
        
        try:
            # Prepare time series
            sku_sales = sales_df[sales_df['sku_id'] == sku_id].copy()
            if len(sku_sales) < 60:  # Need at least 60 days of data
                continue
            
            daily = sku_sales.groupby('date')['units_sold'].sum().reset_index()
            daily = daily.sort_values('date')
            
            # Run forecast
            forecast = engine.forecast(
                series=daily['units_sold'],
                dates=daily['date'],
                horizon=horizon
            )
            
            # Store results
            for j, (date, pred) in enumerate(zip(forecast['dates'], forecast['predictions'])):
                results.append({
                    'sku_id': sku_id,
                    'forecast_date': date,
                    'day_ahead': j + 1,
                    'predicted_demand': round(pred, 2),
                    'model_used': forecast['model'],
                    'model_mae': round(forecast['metrics'].get(forecast['model'], {}).get('mae', 0), 2)
                })
                
        except Exception as e:
            print(f"  Error forecasting {sku_id}: {e}")
            continue
    
    # Save results
    results_df = pd.DataFrame(results)
    project_root = get_project_root()
    output_path = os.path.join(project_root, 'data', 'processed', output_file)
    results_df.to_csv(output_path, index=False)
    
    print(f"\nForecasts saved to: {output_path}")
    print(f"Total forecast records: {len(results_df)}")
    
    # Summary statistics
    if len(results_df) > 0:
        print("\nModel Usage Summary:")
        print(results_df.groupby('model_used').size().to_string())
    
    print("\n" + "=" * 60)
    print("Forecasting complete!")
    print("=" * 60)
    
    return results_df


def forecast_single_sku(sku_id, horizon=30, verbose=True):
    """
    Forecast demand for a single SKU with detailed output.
    
    Args:
        sku_id: SKU to forecast
        horizon: Days ahead to forecast
        verbose: Print detailed output
        
    Returns:
        dict with forecast results
    """
    sales_df = load_sales_data()
    sku_sales = sales_df[sales_df['sku_id'] == sku_id].copy()
    
    if len(sku_sales) == 0:
        raise ValueError(f"No sales data found for SKU: {sku_id}")
    
    daily = sku_sales.groupby('date')['units_sold'].sum().reset_index()
    daily = daily.sort_values('date')
    
    engine = ForecastEngine()
    forecast = engine.forecast(
        series=daily['units_sold'],
        dates=daily['date'],
        horizon=horizon
    )
    
    if verbose:
        print(f"\nForecast for SKU: {sku_id}")
        print("-" * 40)
        print(f"Historical data points: {len(daily)}")
        print(f"Best model: {forecast['model']}")
        print(f"\nModel Comparison (MAE = Mean Absolute Error):")
        for model_name, metrics in forecast['metrics'].items():
            if 'mae' in metrics:
                print(f"  {model_name}: MAE = {metrics['mae']:.2f}")
        print(f"\nNext {horizon} days forecast:")
        print(f"  Average predicted demand: {np.mean(forecast['predictions']):.1f} units/day")
        print(f"  Total predicted demand: {np.sum(forecast['predictions']):.0f} units")
    
    return forecast


if __name__ == "__main__":
    # Run forecasts for sample SKUs
    run_forecasts(horizon=30)
