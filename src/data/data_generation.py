"""
ReplenishIQ Data Generation Script
Generates synthetic operational data on top of real Staples product catalog.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

np.random.seed(42)

# Configuration
NUM_SKUS = 500
START_DATE = datetime(2024, 1, 1)
END_DATE = datetime(2025, 12, 31)
NUM_DAYS = (END_DATE - START_DATE).days + 1

# Define 5 clean categories for the project
CATEGORIES = {
    'Office Supplies': ['Folders', 'Binders', 'Pens', 'Paper Clips', 'Staplers'],
    'Technology': ['Monitors', 'Keyboards', 'Mice', 'Cables', 'Storage'],
    'Furniture': ['Desks', 'Chairs', 'Shelving', 'Filing Cabinets', 'Tables'],
    'Breakroom': ['Coffee', 'Snacks', 'Cups', 'Utensils', 'Cleaning'],
    'Shipping': ['Boxes', 'Tape', 'Envelopes', 'Labels', 'Packaging']
}

# Suppliers
SUPPLIERS = [
    {'id': 'SUP001', 'name': 'FastShip Logistics', 'avg_lead_time': 5, 'variance': 1, 'fill_rate': 0.98, 'otd_rate': 0.95},
    {'id': 'SUP002', 'name': 'Global Office Supply', 'avg_lead_time': 7, 'variance': 2, 'fill_rate': 0.95, 'otd_rate': 0.92},
    {'id': 'SUP003', 'name': 'TechDirect Inc', 'avg_lead_time': 10, 'variance': 3, 'fill_rate': 0.92, 'otd_rate': 0.88},
    {'id': 'SUP004', 'name': 'Furniture Express', 'avg_lead_time': 14, 'variance': 4, 'fill_rate': 0.90, 'otd_rate': 0.85},
    {'id': 'SUP005', 'name': 'Budget Wholesale', 'avg_lead_time': 8, 'variance': 2, 'fill_rate': 0.94, 'otd_rate': 0.90}
]

ORDER_POLICIES = ['EOQ', 'Fixed Quantity', 'Min-Max', 'Periodic Review']

def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_and_clean_raw_data():
    project_root = get_project_root()
    raw_path = os.path.join(project_root, 'data', 'raw', 'staples_products_dataset_sample.csv')
    df = pd.read_csv(raw_path)
    
    # Clean: remove null SKUs and duplicates
    df = df.dropna(subset=['SKU'])
    df = df.drop_duplicates(subset=['SKU'])
    
    # Clean categories - map dirty values to clean ones
    category_mapping = {
        'Decor': 'Office Supplies',
        'Office Supplies': 'Office Supplies',
        'Furniture': 'Furniture',
        'Storage Furniture': 'Furniture',
        'Paper': 'Office Supplies',
        'Facilities': 'Breakroom',
        'Shipping, Packing & Mailing Supplies': 'Shipping',
        'Shipping Supplies': 'Shipping',
        'Arts & Crafts': 'Office Supplies',
        'Computers & Accessories': 'Technology',
        'Coffee, Water & Snacks': 'Breakroom',
        'Printers & Scanners': 'Technology',
        'Phones, Cameras & Electronics': 'Technology',
        'Audio': 'Technology',
        'Tablets & iPads': 'Technology',
        'Hard Drives & Data Storage': 'Technology'
    }
    
    df['Clean_Category'] = df['Primary Category'].map(lambda x: category_mapping.get(x, 'Office Supplies'))
    
    # Clean price
    df['Price_Clean'] = pd.to_numeric(df['Price'], errors='coerce').fillna(25.0)
    
    return df[['SKU', 'Product Title', 'Brand', 'Clean_Category', 'Sub Category 1', 'Price_Clean']]

def generate_synthetic_products(real_df, target_count=500):
    products = []
    
    # First add all real products
    for _, row in real_df.iterrows():
        products.append({
            'sku_id': str(row['SKU']),
            'product_name': row['Product Title'][:200] if pd.notna(row['Product Title']) else 'Unknown Product',
            'brand': row['Brand'] if pd.notna(row['Brand']) else 'Generic',
            'category': row['Clean_Category'],
            'sub_category': row['Sub Category 1'] if pd.notna(row['Sub Category 1']) else 'General',
            'unit_price': float(row['Price_Clean'])
        })
    
    # Generate synthetic products to reach target
    synthetic_needed = target_count - len(products)
    synthetic_brands = ['Staples', 'Office Depot', 'AmazonBasics', 'Fellowes', 'Avery', '3M', 'HP', 'Dell', 'Logitech', 'HON']
    
    for i in range(synthetic_needed):
        category = np.random.choice(list(CATEGORIES.keys()))
        sub_cat = np.random.choice(CATEGORIES[category])
        brand = np.random.choice(synthetic_brands)
        
        # Price ranges by category
        price_ranges = {
            'Office Supplies': (5, 50),
            'Technology': (20, 500),
            'Furniture': (100, 1000),
            'Breakroom': (3, 30),
            'Shipping': (5, 100)
        }
        price_min, price_max = price_ranges[category]
        
        products.append({
            'sku_id': f'SYN{10000 + i}',
            'product_name': f'{brand} {sub_cat} - Model {np.random.randint(100, 999)}',
            'brand': brand,
            'category': category,
            'sub_category': sub_cat,
            'unit_price': round(np.random.uniform(price_min, price_max), 2)
        })
    
    return pd.DataFrame(products)

def generate_dim_products(products_df):
    dim_products = products_df.copy()
    
    # Add replenishment parameters
    dim_products['lead_time_days'] = dim_products['category'].map({
        'Office Supplies': 5, 'Technology': 10, 'Furniture': 14, 'Breakroom': 4, 'Shipping': 6
    }) + np.random.randint(-2, 3, len(dim_products))
    dim_products['lead_time_days'] = dim_products['lead_time_days'].clip(lower=2)
    
    # Safety stock based on price tier
    dim_products['safety_stock'] = np.where(
        dim_products['unit_price'] < 20, np.random.randint(50, 150, len(dim_products)),
        np.where(dim_products['unit_price'] < 100, np.random.randint(20, 80, len(dim_products)),
                 np.random.randint(5, 30, len(dim_products)))
    )
    
    dim_products['min_order_qty'] = np.where(
        dim_products['unit_price'] < 20, np.random.randint(24, 100, len(dim_products)),
        np.where(dim_products['unit_price'] < 100, np.random.randint(10, 50, len(dim_products)),
                 np.random.randint(1, 20, len(dim_products)))
    )
    
    dim_products['max_stock_level'] = dim_products['safety_stock'] * np.random.randint(3, 6, len(dim_products))
    dim_products['reorder_point'] = dim_products['safety_stock'] + (dim_products['lead_time_days'] * np.random.randint(2, 8, len(dim_products)))
    
    # Assign suppliers
    dim_products['supplier_id'] = np.random.choice([s['id'] for s in SUPPLIERS], len(dim_products))
    
    # SLG targets (service level goals)
    dim_products['slg_target'] = np.random.choice([0.95, 0.97, 0.98, 0.99], len(dim_products), p=[0.3, 0.3, 0.25, 0.15])
    
    # Order policies
    dim_products['order_policy'] = np.random.choice(ORDER_POLICIES, len(dim_products))
    
    return dim_products

def generate_fact_sales(dim_products, start_date, num_days):
    dates = [start_date + timedelta(days=i) for i in range(num_days)]
    sales_records = []
    
    for sku_id in dim_products['sku_id']:
        product = dim_products[dim_products['sku_id'] == sku_id].iloc[0]
        base_demand = np.random.randint(5, 50) if product['unit_price'] < 50 else np.random.randint(1, 15)
        
        for date in dates:
            # Seasonality: Q4 +40%, Q1 -30%, back-to-school Aug +20%
            month = date.month
            if month in [10, 11, 12]:
                seasonal_mult = 1.4
            elif month in [1, 2, 3]:
                seasonal_mult = 0.7
            elif month == 8:
                seasonal_mult = 1.2
            else:
                seasonal_mult = 1.0
            
            # Day of week: weekends -40%
            dow_mult = 0.6 if date.weekday() >= 5 else 1.0
            
            # Random variation
            random_mult = np.random.uniform(0.5, 1.5)
            
            units = max(0, int(base_demand * seasonal_mult * dow_mult * random_mult))
            
            if units > 0:
                sales_records.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'sku_id': sku_id,
                    'units_sold': units,
                    'revenue': round(units * product['unit_price'], 2),
                    'category': product['category']
                })
    
    return pd.DataFrame(sales_records)

def generate_fact_inventory(dim_products, fact_sales, start_date, num_days):
    dates = [start_date + timedelta(days=i) for i in range(num_days)]
    inventory_records = []
    
    # Group sales by sku and date
    sales_lookup = fact_sales.groupby(['sku_id', 'date'])['units_sold'].sum().to_dict()
    
    for sku_id in dim_products['sku_id']:
        product = dim_products[dim_products['sku_id'] == sku_id].iloc[0]
        on_hand = int(product['max_stock_level'] * 0.7)  # Start at 70% of max
        
        for date in dates:
            date_str = date.strftime('%Y-%m-%d')
            units_sold = sales_lookup.get((sku_id, date_str), 0)
            
            # Simulate replenishment when below reorder point
            reorder_triggered = on_hand <= product['reorder_point']
            if reorder_triggered and np.random.random() > 0.3:
                on_hand += int(product['min_order_qty'] * np.random.uniform(1, 2))
            
            on_hand = max(0, on_hand - units_sold)
            
            stockout_flag = on_hand == 0
            instock_flag = on_hand > 0
            overstock_flag = on_hand > product['max_stock_level']
            
            avg_daily_demand = max(1, units_sold) if units_sold > 0 else 5
            days_of_supply = round(on_hand / avg_daily_demand, 1)
            carrying_cost = round(on_hand * product['unit_price'] * 0.0005, 2)
            
            inventory_records.append({
                'date': date_str,
                'sku_id': sku_id,
                'on_hand_qty': on_hand,
                'units_sold': units_sold,
                'reorder_triggered': reorder_triggered,
                'stockout_flag': stockout_flag,
                'overstock_flag': overstock_flag,
                'days_of_supply': days_of_supply,
                'safety_stock': product['safety_stock'],
                'reorder_point': product['reorder_point'],
                'instock_flag': instock_flag,
                'carrying_cost_daily': carrying_cost
            })
    
    return pd.DataFrame(inventory_records)

def generate_dim_suppliers():
    return pd.DataFrame([{
        'supplier_id': s['id'],
        'supplier_name': s['name'],
        'avg_lead_time': s['avg_lead_time'],
        'lead_time_variance': s['variance'],
        'fill_rate': s['fill_rate'],
        'on_time_delivery_rate': s['otd_rate'],
        'min_order_value': np.random.randint(100, 500) * 10
    } for s in SUPPLIERS])

def generate_fact_replenishment_orders(dim_products, fact_inventory, start_date, num_days):
    orders = []
    order_id = 1
    
    # Find all reorder triggers
    reorder_events = fact_inventory[fact_inventory['reorder_triggered'] == True]
    
    for _, event in reorder_events.iterrows():
        product = dim_products[dim_products['sku_id'] == event['sku_id']].iloc[0]
        supplier = next(s for s in SUPPLIERS if s['id'] == product['supplier_id'])
        
        order_date = datetime.strptime(event['date'], '%Y-%m-%d')
        expected_lead = supplier['avg_lead_time']
        actual_lead = max(1, expected_lead + np.random.randint(-supplier['variance'], supplier['variance'] + 1))
        
        expected_delivery = order_date + timedelta(days=expected_lead)
        actual_delivery = order_date + timedelta(days=actual_lead)
        
        fill_rate_actual = min(1.0, supplier['fill_rate'] + np.random.uniform(-0.05, 0.05))
        
        orders.append({
            'order_id': f'ORD{order_id:06d}',
            'order_date': event['date'],
            'sku_id': event['sku_id'],
            'supplier_id': product['supplier_id'],
            'order_qty': int(product['min_order_qty']),
            'expected_delivery_date': expected_delivery.strftime('%Y-%m-%d'),
            'actual_delivery_date': actual_delivery.strftime('%Y-%m-%d'),
            'lead_time_actual': actual_lead,
            'fill_rate_actual': round(fill_rate_actual, 4)
        })
        order_id += 1
    
    return pd.DataFrame(orders)

def main():
    print("=" * 60)
    print("ReplenishIQ Data Generation")
    print("=" * 60)
    
    project_root = get_project_root()
    output_dir = os.path.join(project_root, 'data', 'processed')
    os.makedirs(output_dir, exist_ok=True)
    
    # Step 1: Load and clean raw data
    print("\n[1/6] Loading and cleaning raw Staples data...")
    raw_df = load_and_clean_raw_data()
    print(f"      Cleaned {len(raw_df)} unique products from raw data")
    
    # Step 2: Generate synthetic products to reach 500
    print("\n[2/6] Generating synthetic products...")
    products_df = generate_synthetic_products(raw_df, NUM_SKUS)
    print(f"      Total products: {len(products_df)}")
    
    # Step 3: Generate dim_products with replenishment parameters
    print("\n[3/6] Adding replenishment parameters...")
    dim_products = generate_dim_products(products_df)
    dim_products.to_csv(os.path.join(output_dir, 'dim_products.csv'), index=False)
    print(f"      Saved dim_products.csv ({len(dim_products)} rows)")
    
    # Step 4: Generate dim_suppliers
    print("\n[4/6] Generating suppliers...")
    dim_suppliers = generate_dim_suppliers()
    dim_suppliers.to_csv(os.path.join(output_dir, 'dim_suppliers.csv'), index=False)
    print(f"      Saved dim_suppliers.csv ({len(dim_suppliers)} rows)")
    
    # Step 5: Generate fact_sales
    print("\n[5/6] Generating sales data (this may take a minute)...")
    fact_sales = generate_fact_sales(dim_products, START_DATE, NUM_DAYS)
    fact_sales.to_csv(os.path.join(output_dir, 'fact_sales.csv'), index=False)
    print(f"      Saved fact_sales.csv ({len(fact_sales)} rows)")
    
    # Step 6: Generate fact_inventory
    print("\n[6/6] Generating inventory data...")
    fact_inventory = generate_fact_inventory(dim_products, fact_sales, START_DATE, NUM_DAYS)
    fact_inventory.to_csv(os.path.join(output_dir, 'fact_inventory.csv'), index=False)
    print(f"      Saved fact_inventory.csv ({len(fact_inventory)} rows)")
    
    # Step 7: Generate replenishment orders
    print("\n[7/7] Generating replenishment orders...")
    fact_orders = generate_fact_replenishment_orders(dim_products, fact_inventory, START_DATE, NUM_DAYS)
    fact_orders.to_csv(os.path.join(output_dir, 'fact_replenishment_orders.csv'), index=False)
    print(f"      Saved fact_replenishment_orders.csv ({len(fact_orders)} rows)")
    
    print("\n" + "=" * 60)
    print("Data generation complete!")
    print(f"Output directory: {output_dir}")
    print("=" * 60)

if __name__ == "__main__":
    main()
