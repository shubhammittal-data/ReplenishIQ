# Sample Data

This folder contains sample data files showing the expected schema.

To generate the full dataset (500 SKUs, 12 months of transactions), run:

```bash
python -m src.data.generate_data
```

This will create the following files in `data/processed/`:
- `dim_products.csv` - Product master data
- `dim_suppliers.csv` - Supplier information
- `fact_sales.csv` - Daily sales transactions
- `fact_inventory.csv` - Daily inventory snapshots
- `fact_replenishment_orders.csv` - Purchase orders
