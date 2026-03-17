"""
ReplenishIQ Data Validator
Runs data quality checks on the generated/loaded data.
"""

import pandas as pd
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_engine():
    host = os.getenv('POSTGRES_HOST', 'localhost')
    port = os.getenv('POSTGRES_PORT', '5432')
    db = os.getenv('POSTGRES_DB', 'replenishiq')
    user = os.getenv('POSTGRES_USER', 'postgres')
    password = os.getenv('POSTGRES_PASSWORD', '')
    
    connection_string = f'postgresql://{user}:{password}@{host}:{port}/{db}'
    return create_engine(connection_string)

def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def validate_csv_files():
    print("\n[1] Validating CSV files...")
    project_root = get_project_root()
    processed_dir = os.path.join(project_root, 'data', 'processed')
    
    expected_files = {
        'dim_products.csv': {'min_rows': 500, 'required_cols': ['sku_id', 'product_name', 'category', 'safety_stock']},
        'dim_suppliers.csv': {'min_rows': 5, 'required_cols': ['supplier_id', 'supplier_name', 'avg_lead_time']},
        'fact_sales.csv': {'min_rows': 100000, 'required_cols': ['date', 'sku_id', 'units_sold', 'revenue']},
        'fact_inventory.csv': {'min_rows': 300000, 'required_cols': ['date', 'sku_id', 'on_hand_qty', 'stockout_flag']},
        'fact_replenishment_orders.csv': {'min_rows': 10000, 'required_cols': ['order_id', 'sku_id', 'order_qty']}
    }
    
    all_passed = True
    for filename, checks in expected_files.items():
        filepath = os.path.join(processed_dir, filename)
        if not os.path.exists(filepath):
            print(f"  FAIL: {filename} not found")
            all_passed = False
            continue
        
        df = pd.read_csv(filepath)
        
        # Check row count
        if len(df) < checks['min_rows']:
            print(f"  WARN: {filename} has {len(df)} rows (expected >= {checks['min_rows']})")
        else:
            print(f"  PASS: {filename} has {len(df):,} rows")
        
        # Check required columns
        missing_cols = [c for c in checks['required_cols'] if c not in df.columns]
        if missing_cols:
            print(f"  FAIL: {filename} missing columns: {missing_cols}")
            all_passed = False
    
    return all_passed

def validate_data_quality():
    print("\n[2] Validating data quality...")
    project_root = get_project_root()
    processed_dir = os.path.join(project_root, 'data', 'processed')
    
    all_passed = True
    
    # Check dim_products
    df = pd.read_csv(os.path.join(processed_dir, 'dim_products.csv'))
    null_skus = df['sku_id'].isna().sum()
    if null_skus > 0:
        print(f"  FAIL: dim_products has {null_skus} null SKU IDs")
        all_passed = False
    else:
        print(f"  PASS: No null SKU IDs in dim_products")
    
    dup_skus = df['sku_id'].duplicated().sum()
    if dup_skus > 0:
        print(f"  FAIL: dim_products has {dup_skus} duplicate SKU IDs")
        all_passed = False
    else:
        print(f"  PASS: No duplicate SKU IDs")
    
    # Check date range in fact_sales
    df_sales = pd.read_csv(os.path.join(processed_dir, 'fact_sales.csv'))
    df_sales['date'] = pd.to_datetime(df_sales['date'])
    min_date = df_sales['date'].min()
    max_date = df_sales['date'].max()
    print(f"  INFO: Sales date range: {min_date.date()} to {max_date.date()}")
    
    if min_date.year != 2024 or max_date.year != 2025:
        print(f"  WARN: Date range does not span 2024-2025 as expected")
    else:
        print(f"  PASS: Date range covers 2024-2025")
    
    # Check for negative values
    df_inv = pd.read_csv(os.path.join(processed_dir, 'fact_inventory.csv'))
    neg_qty = (df_inv['on_hand_qty'] < 0).sum()
    if neg_qty > 0:
        print(f"  FAIL: {neg_qty} negative on_hand_qty values")
        all_passed = False
    else:
        print(f"  PASS: No negative inventory quantities")
    
    # Check stockout consistency
    stockout_mismatch = ((df_inv['stockout_flag'] == True) & (df_inv['on_hand_qty'] > 0)).sum()
    if stockout_mismatch > 0:
        print(f"  WARN: {stockout_mismatch} stockout flags inconsistent with on_hand_qty")
    else:
        print(f"  PASS: Stockout flags consistent with inventory")
    
    return all_passed

def validate_referential_integrity():
    print("\n[3] Validating referential integrity...")
    project_root = get_project_root()
    processed_dir = os.path.join(project_root, 'data', 'processed')
    
    all_passed = True
    
    dim_products = pd.read_csv(os.path.join(processed_dir, 'dim_products.csv'))
    dim_suppliers = pd.read_csv(os.path.join(processed_dir, 'dim_suppliers.csv'))
    fact_sales = pd.read_csv(os.path.join(processed_dir, 'fact_sales.csv'))
    
    product_skus = set(dim_products['sku_id'])
    supplier_ids = set(dim_suppliers['supplier_id'])
    
    # Check products reference valid suppliers
    invalid_suppliers = dim_products[~dim_products['supplier_id'].isin(supplier_ids)]
    if len(invalid_suppliers) > 0:
        print(f"  FAIL: {len(invalid_suppliers)} products reference invalid suppliers")
        all_passed = False
    else:
        print(f"  PASS: All products reference valid suppliers")
    
    # Check sales reference valid products
    invalid_sales = fact_sales[~fact_sales['sku_id'].isin(product_skus)]
    if len(invalid_sales) > 0:
        print(f"  FAIL: {len(invalid_sales)} sales reference invalid SKUs")
        all_passed = False
    else:
        print(f"  PASS: All sales reference valid products")
    
    return all_passed

def main():
    print("=" * 60)
    print("ReplenishIQ Data Validation")
    print("=" * 60)
    
    csv_ok = validate_csv_files()
    quality_ok = validate_data_quality()
    integrity_ok = validate_referential_integrity()
    
    print("\n" + "=" * 60)
    if csv_ok and quality_ok and integrity_ok:
        print("All validations PASSED!")
    else:
        print("Some validations FAILED - review output above")
    print("=" * 60)

if __name__ == "__main__":
    main()
