"""
ReplenishIQ Tableau Export Module
Prepares and exports data files optimized for Tableau dashboards.

Exports:
1. KPI Summary - High-level metrics
2. Inventory Health - Daily inventory status
3. Sales Trends - Sales by category/time
4. Supplier Scorecard - Supplier performance
5. Exception Dashboard - Alerts and actions
6. Forecast Data - Predictions for planning
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import warnings
warnings.filterwarnings('ignore')

def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_all_data():
    """Load all data files."""
    project_root = get_project_root()
    data_dir = os.path.join(project_root, 'data', 'processed')
    
    data = {
        'products': pd.read_csv(os.path.join(data_dir, 'dim_products.csv')),
        'suppliers': pd.read_csv(os.path.join(data_dir, 'dim_suppliers.csv')),
        'sales': pd.read_csv(os.path.join(data_dir, 'fact_sales.csv')),
        'inventory': pd.read_csv(os.path.join(data_dir, 'fact_inventory.csv')),
        'orders': pd.read_csv(os.path.join(data_dir, 'fact_replenishment_orders.csv'))
    }
    
    # Load optional files
    try:
        data['clusters'] = pd.read_csv(os.path.join(data_dir, 'sku_clusters.csv'))
    except:
        data['clusters'] = None
    
    try:
        data['forecasts'] = pd.read_csv(os.path.join(data_dir, 'forecasts.csv'))
    except:
        data['forecasts'] = None
    
    try:
        data['alerts'] = pd.read_csv(os.path.join(data_dir, 'alerts.csv'))
    except:
        data['alerts'] = None
    
    # Convert dates
    data['sales']['date'] = pd.to_datetime(data['sales']['date'])
    data['inventory']['date'] = pd.to_datetime(data['inventory']['date'])
    data['orders']['order_date'] = pd.to_datetime(data['orders']['order_date'])
    
    return data


def export_kpi_summary(data):
    """
    Export 1: KPI Summary
    High-level metrics for executive dashboard.
    """
    inventory = data['inventory']
    sales = data['sales']
    products = data['products']
    
    # Calculate KPIs
    total_revenue = sales['revenue'].sum()
    total_units = sales['units_sold'].sum()
    
    instock_rate = inventory['instock_flag'].mean() * 100
    stockout_rate = inventory['stockout_flag'].mean() * 100
    overstock_rate = inventory['overstock_flag'].mean() * 100
    
    total_carrying_cost = inventory['carrying_cost_daily'].sum()
    avg_inventory_value = (inventory['on_hand_qty'] * 
                           inventory.merge(products[['sku_id', 'unit_price']], on='sku_id')['unit_price']).mean()
    
    # Monthly trends
    monthly_sales = sales.groupby(sales['date'].dt.to_period('M')).agg({
        'revenue': 'sum',
        'units_sold': 'sum'
    }).reset_index()
    monthly_sales['date'] = monthly_sales['date'].astype(str)
    
    kpi_summary = pd.DataFrame([{
        'metric': 'Total Revenue',
        'value': total_revenue,
        'format': 'currency'
    }, {
        'metric': 'Total Units Sold',
        'value': total_units,
        'format': 'number'
    }, {
        'metric': 'In-Stock Rate',
        'value': instock_rate,
        'format': 'percent'
    }, {
        'metric': 'Stockout Rate',
        'value': stockout_rate,
        'format': 'percent'
    }, {
        'metric': 'Overstock Rate',
        'value': overstock_rate,
        'format': 'percent'
    }, {
        'metric': 'Total Carrying Cost',
        'value': total_carrying_cost,
        'format': 'currency'
    }, {
        'metric': 'SKU Count',
        'value': len(products),
        'format': 'number'
    }])
    
    return kpi_summary, monthly_sales


def export_inventory_health(data):
    """
    Export 2: Inventory Health
    Daily inventory status by SKU and category.
    """
    inventory = data['inventory']
    products = data['products']
    
    # Merge with product info
    inv_health = inventory.merge(
        products[['sku_id', 'product_name', 'category', 'unit_price', 'safety_stock', 'max_stock_level', 'slg_target']],
        on='sku_id'
    )
    
    # Add calculated fields
    inv_health['inventory_value'] = inv_health['on_hand_qty'] * inv_health['unit_price']
    inv_health['safety_stock_pct'] = (inv_health['on_hand_qty'] / inv_health['safety_stock_y'].replace(0, 1)) * 100
    inv_health['health_status'] = np.where(
        inv_health['stockout_flag'], 'Stockout',
        np.where(inv_health['on_hand_qty'] < inv_health['safety_stock_y'], 'Low Stock',
        np.where(inv_health['overstock_flag'], 'Overstock', 'Healthy'))
    )
    
    # Aggregate by date and category
    daily_health = inv_health.groupby(['date', 'category']).agg({
        'on_hand_qty': 'sum',
        'inventory_value': 'sum',
        'stockout_flag': 'sum',
        'overstock_flag': 'sum',
        'instock_flag': 'mean',
        'carrying_cost_daily': 'sum'
    }).reset_index()
    
    daily_health.columns = ['date', 'category', 'total_units', 'total_value', 
                            'stockout_skus', 'overstock_skus', 'instock_rate', 'carrying_cost']
    
    return inv_health, daily_health


def export_sales_trends(data):
    """
    Export 3: Sales Trends
    Sales analysis by time, category, and product.
    """
    sales = data['sales'].copy()
    products = data['products']
    
    # Drop category from sales if exists (we'll use product's category)
    if 'category' in sales.columns:
        sales = sales.drop(columns=['category'])
    
    # Merge with product info
    sales_detail = sales.merge(
        products[['sku_id', 'product_name', 'brand', 'category', 'sub_category']],
        on='sku_id'
    )
    
    # Daily sales by category
    daily_category = sales_detail.groupby(['date', 'category']).agg({
        'units_sold': 'sum',
        'revenue': 'sum'
    }).reset_index()
    
    # Monthly sales trend
    sales_detail['month'] = sales_detail['date'].dt.to_period('M').astype(str)
    sales_detail['week'] = sales_detail['date'].dt.isocalendar().week
    sales_detail['day_of_week'] = sales_detail['date'].dt.day_name()
    
    monthly_trend = sales_detail.groupby(['month', 'category']).agg({
        'units_sold': 'sum',
        'revenue': 'sum',
        'sku_id': 'nunique'
    }).reset_index()
    monthly_trend.columns = ['month', 'category', 'units_sold', 'revenue', 'active_skus']
    
    # Top products
    top_products = sales_detail.groupby(['sku_id', 'product_name', 'category']).agg({
        'units_sold': 'sum',
        'revenue': 'sum'
    }).reset_index().sort_values('revenue', ascending=False).head(50)
    
    return daily_category, monthly_trend, top_products


def export_supplier_scorecard(data):
    """
    Export 4: Supplier Scorecard
    Supplier performance metrics.
    """
    orders = data['orders']
    suppliers = data['suppliers']
    products = data['products']
    
    # Calculate supplier metrics
    orders['days_late'] = (
        pd.to_datetime(orders['actual_delivery_date']) - 
        pd.to_datetime(orders['expected_delivery_date'])
    ).dt.days
    orders['on_time'] = orders['days_late'] <= 0
    
    supplier_metrics = orders.groupby('supplier_id').agg({
        'order_id': 'count',
        'order_qty': 'sum',
        'lead_time_actual': ['mean', 'std'],
        'fill_rate_actual': 'mean',
        'on_time': 'mean',
        'days_late': 'mean'
    }).reset_index()
    
    supplier_metrics.columns = [
        'supplier_id', 'total_orders', 'total_qty', 
        'actual_avg_lead_time', 'lead_time_std', 'avg_fill_rate', 
        'on_time_rate', 'avg_days_late'
    ]
    
    # Merge with supplier info
    scorecard = supplier_metrics.merge(suppliers, on='supplier_id')
    
    # Calculate reliability score
    scorecard['reliability_score'] = (
        scorecard['avg_fill_rate'] * 30 +
        scorecard['on_time_rate'] * 40 +
        (1 - scorecard['lead_time_std'].fillna(0) / scorecard['actual_avg_lead_time'].replace(0, 1)) * 30
    ).round(1)
    
    # Monthly supplier performance
    orders['month'] = pd.to_datetime(orders['order_date']).dt.to_period('M').astype(str)
    monthly_supplier = orders.groupby(['month', 'supplier_id']).agg({
        'order_id': 'count',
        'on_time': 'mean',
        'fill_rate_actual': 'mean'
    }).reset_index()
    monthly_supplier.columns = ['month', 'supplier_id', 'orders', 'on_time_rate', 'fill_rate']
    
    return scorecard, monthly_supplier


def export_exception_dashboard(data):
    """
    Export 5: Exception Dashboard
    Alerts and recommended actions.
    """
    alerts = data.get('alerts')
    products = data['products']
    
    if alerts is None or len(alerts) == 0:
        # Generate basic exception data from inventory
        inventory = data['inventory']
        
        # Get latest inventory status
        latest_date = inventory['date'].max()
        latest_inv = inventory[inventory['date'] == latest_date]
        
        exceptions = latest_inv.merge(
            products[['sku_id', 'product_name', 'category', 'slg_target']],
            on='sku_id'
        )
        
        exceptions['exception_type'] = np.where(
            exceptions['stockout_flag'], 'Stockout',
            np.where(exceptions['on_hand_qty'] < exceptions['safety_stock'], 'Low Stock',
            np.where(exceptions['overstock_flag'], 'Overstock', 'None'))
        )
        
        exceptions = exceptions[exceptions['exception_type'] != 'None']
        
        return exceptions[['sku_id', 'product_name', 'category', 'exception_type', 
                          'on_hand_qty', 'safety_stock', 'reorder_point']]
    
    # Use alerts data
    alerts_df = alerts.merge(
        products[['sku_id', 'category']],
        on='sku_id',
        how='left'
    )
    
    return alerts_df


def export_forecast_data(data):
    """
    Export 6: Forecast Data
    Demand predictions for planning.
    """
    forecasts = data.get('forecasts')
    products = data['products']
    
    if forecasts is None:
        return None
    
    # Merge with product info
    forecast_detail = forecasts.merge(
        products[['sku_id', 'product_name', 'category', 'unit_price']],
        on='sku_id'
    )
    
    forecast_detail['predicted_revenue'] = forecast_detail['predicted_demand'] * forecast_detail['unit_price']
    
    return forecast_detail


def run_tableau_export():
    """Run full Tableau export pipeline."""
    print("=" * 60)
    print("ReplenishIQ Tableau Export")
    print("=" * 60)
    
    # Load data
    print("\nLoading data...")
    data = load_all_data()
    
    project_root = get_project_root()
    output_dir = os.path.join(project_root, 'tableau')
    os.makedirs(output_dir, exist_ok=True)
    
    # Export 1: KPI Summary
    print("\nExporting KPI Summary...")
    kpi_summary, monthly_sales = export_kpi_summary(data)
    kpi_summary.to_csv(os.path.join(output_dir, 'kpi_summary.csv'), index=False)
    monthly_sales.to_csv(os.path.join(output_dir, 'monthly_sales_trend.csv'), index=False)
    print(f"  Saved kpi_summary.csv and monthly_sales_trend.csv")
    
    # Export 2: Inventory Health
    print("\nExporting Inventory Health...")
    inv_detail, daily_health = export_inventory_health(data)
    daily_health.to_csv(os.path.join(output_dir, 'daily_inventory_health.csv'), index=False)
    print(f"  Saved daily_inventory_health.csv ({len(daily_health)} rows)")
    
    # Export 3: Sales Trends
    print("\nExporting Sales Trends...")
    daily_cat, monthly_trend, top_products = export_sales_trends(data)
    daily_cat.to_csv(os.path.join(output_dir, 'daily_sales_by_category.csv'), index=False)
    monthly_trend.to_csv(os.path.join(output_dir, 'monthly_sales_trend_by_category.csv'), index=False)
    top_products.to_csv(os.path.join(output_dir, 'top_50_products.csv'), index=False)
    print(f"  Saved sales trend files")
    
    # Export 4: Supplier Scorecard
    print("\nExporting Supplier Scorecard...")
    scorecard, monthly_supplier = export_supplier_scorecard(data)
    scorecard.to_csv(os.path.join(output_dir, 'supplier_scorecard.csv'), index=False)
    monthly_supplier.to_csv(os.path.join(output_dir, 'monthly_supplier_performance.csv'), index=False)
    print(f"  Saved supplier scorecard files")
    
    # Export 5: Exception Dashboard
    print("\nExporting Exception Dashboard...")
    exceptions = export_exception_dashboard(data)
    if exceptions is not None:
        exceptions.to_csv(os.path.join(output_dir, 'exception_dashboard.csv'), index=False)
        print(f"  Saved exception_dashboard.csv ({len(exceptions)} rows)")
    
    # Export 6: Forecast Data
    print("\nExporting Forecast Data...")
    forecasts = export_forecast_data(data)
    if forecasts is not None:
        forecasts.to_csv(os.path.join(output_dir, 'forecast_data.csv'), index=False)
        print(f"  Saved forecast_data.csv ({len(forecasts)} rows)")
    
    # Export clusters if available
    if data.get('clusters') is not None:
        data['clusters'].to_csv(os.path.join(output_dir, 'sku_clusters.csv'), index=False)
        print(f"  Saved sku_clusters.csv")
    
    print(f"\nAll files exported to: {output_dir}")
    
    print("\n" + "=" * 60)
    print("Tableau Export Complete!")
    print("=" * 60)
    
    # Print file list
    print("\nExported Files:")
    for f in os.listdir(output_dir):
        if f.endswith('.csv'):
            size = os.path.getsize(os.path.join(output_dir, f)) / 1024
            print(f"  - {f} ({size:.1f} KB)")


if __name__ == "__main__":
    run_tableau_export()
