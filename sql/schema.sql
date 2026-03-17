-- ReplenishIQ PostgreSQL Schema
-- Creates all tables for the replenishment optimization system

-- Drop existing tables if they exist (for clean rebuild)
DROP TABLE IF EXISTS fact_replenishment_orders CASCADE;
DROP TABLE IF EXISTS fact_inventory CASCADE;
DROP TABLE IF EXISTS fact_sales CASCADE;
DROP TABLE IF EXISTS dim_products CASCADE;
DROP TABLE IF EXISTS dim_suppliers CASCADE;

-- Suppliers dimension table
CREATE TABLE dim_suppliers (
    supplier_id VARCHAR(20) PRIMARY KEY,
    supplier_name VARCHAR(200),
    avg_lead_time INTEGER,
    lead_time_variance INTEGER,
    fill_rate DECIMAL(5,4),
    on_time_delivery_rate DECIMAL(5,4),
    min_order_value DECIMAL(10,2)
);

-- Products dimension table
CREATE TABLE dim_products (
    sku_id VARCHAR(50) PRIMARY KEY,
    product_name VARCHAR(500),
    brand VARCHAR(100),
    category VARCHAR(100),
    sub_category VARCHAR(100),
    unit_price DECIMAL(10,2),
    lead_time_days INTEGER,
    safety_stock INTEGER,
    min_order_qty INTEGER,
    max_stock_level INTEGER,
    reorder_point INTEGER,
    supplier_id VARCHAR(20) REFERENCES dim_suppliers(supplier_id),
    slg_target DECIMAL(5,4),
    order_policy VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Daily sales fact table
CREATE TABLE fact_sales (
    sale_id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    sku_id VARCHAR(50) REFERENCES dim_products(sku_id),
    units_sold INTEGER,
    revenue DECIMAL(12,2),
    category VARCHAR(100)
);

-- Daily inventory snapshot fact table
CREATE TABLE fact_inventory (
    inventory_id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    sku_id VARCHAR(50) REFERENCES dim_products(sku_id),
    on_hand_qty INTEGER,
    units_sold INTEGER,
    reorder_triggered BOOLEAN,
    stockout_flag BOOLEAN,
    overstock_flag BOOLEAN,
    days_of_supply DECIMAL(10,1),
    safety_stock INTEGER,
    reorder_point INTEGER,
    instock_flag BOOLEAN,
    carrying_cost_daily DECIMAL(10,2)
);

-- Replenishment orders fact table
CREATE TABLE fact_replenishment_orders (
    order_id VARCHAR(50) PRIMARY KEY,
    order_date DATE,
    sku_id VARCHAR(50) REFERENCES dim_products(sku_id),
    supplier_id VARCHAR(20) REFERENCES dim_suppliers(supplier_id),
    order_qty INTEGER,
    expected_delivery_date DATE,
    actual_delivery_date DATE,
    lead_time_actual INTEGER,
    fill_rate_actual DECIMAL(5,4)
);

-- Indexes for performance
CREATE INDEX idx_fact_sales_date ON fact_sales(date);
CREATE INDEX idx_fact_sales_sku ON fact_sales(sku_id);
CREATE INDEX idx_fact_sales_category ON fact_sales(category);
CREATE INDEX idx_fact_inventory_date ON fact_inventory(date);
CREATE INDEX idx_fact_inventory_sku ON fact_inventory(sku_id);
CREATE INDEX idx_fact_inventory_stockout ON fact_inventory(stockout_flag);
CREATE INDEX idx_fact_inventory_overstock ON fact_inventory(overstock_flag);
CREATE INDEX idx_fact_orders_date ON fact_replenishment_orders(order_date);
CREATE INDEX idx_fact_orders_sku ON fact_replenishment_orders(sku_id);
CREATE INDEX idx_dim_products_category ON dim_products(category);
CREATE INDEX idx_dim_products_supplier ON dim_products(supplier_id);

-- Verify tables created
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
