"""
ReplenishIQ Data Loader
Loads CSV data from processed folder into PostgreSQL database.
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

def load_table(engine, table_name, csv_filename, if_exists='append'):
    project_root = get_project_root()
    csv_path = os.path.join(project_root, 'data', 'processed', csv_filename)
    
    if not os.path.exists(csv_path):
        print(f"  ERROR: {csv_path} not found!")
        return 0
    
    df = pd.read_csv(csv_path)
    df.to_sql(table_name, engine, if_exists=if_exists, index=False)
    return len(df)

def main():
    print("=" * 60)
    print("ReplenishIQ Data Loader")
    print("=" * 60)
    
    engine = get_db_engine()
    
    # Test connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("\nDatabase connection successful!")
    except Exception as e:
        print(f"\nERROR: Could not connect to database: {e}")
        print("Make sure PostgreSQL is running and .env is configured.")
        return
    
    # Load tables in order (respecting foreign keys)
    tables = [
        ('dim_suppliers', 'dim_suppliers.csv'),
        ('dim_products', 'dim_products.csv'),
        ('fact_sales', 'fact_sales.csv'),
        ('fact_inventory', 'fact_inventory.csv'),
        ('fact_replenishment_orders', 'fact_replenishment_orders.csv')
    ]
    
    for table_name, csv_file in tables:
        print(f"\nLoading {table_name}...")
        try:
            rows = load_table(engine, table_name, csv_file, if_exists='append')
            print(f"  Loaded {rows:,} rows into {table_name}")
        except Exception as e:
            print(f"  ERROR loading {table_name}: {e}")
    
    # Verify row counts
    print("\n" + "-" * 40)
    print("Verification - Row counts:")
    with engine.connect() as conn:
        for table_name, _ in tables:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            count = result.scalar()
            print(f"  {table_name}: {count:,} rows")
    
    print("\n" + "=" * 60)
    print("Data loading complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
