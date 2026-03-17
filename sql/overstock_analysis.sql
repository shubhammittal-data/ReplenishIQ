-- Overstock Analysis
-- Identifies SKUs with excess inventory (high days of supply, above max stock level)

-- Overstock by SKU
SELECT 
    p.sku_id,
    p.product_name,
    p.category,
    p.max_stock_level,
    ROUND(AVG(i.on_hand_qty), 1) as avg_inventory,
    ROUND(AVG(s.units_sold), 1) as avg_daily_demand,
    CASE 
        WHEN AVG(s.units_sold) > 0 
        THEN ROUND(AVG(i.on_hand_qty) / AVG(s.units_sold), 1)
        ELSE NULL 
    END as days_of_supply,
    SUM(CASE WHEN i.overstock_flag THEN 1 ELSE 0 END) as overstock_days,
    ROUND(100.0 * SUM(CASE WHEN i.overstock_flag THEN 1 ELSE 0 END) / COUNT(*), 2) as overstock_rate_pct,
    SUM(i.carrying_cost_daily) as total_carrying_cost,
    p.unit_price * AVG(i.on_hand_qty) as avg_inventory_value
FROM dim_products p
LEFT JOIN fact_inventory i ON p.sku_id = i.sku_id
LEFT JOIN fact_sales s ON p.sku_id = s.sku_id AND i.date = s.date
GROUP BY p.sku_id, p.product_name, p.category, p.max_stock_level, p.unit_price
ORDER BY total_carrying_cost DESC;

-- Overstock by category
SELECT 
    p.category,
    COUNT(DISTINCT p.sku_id) as sku_count,
    ROUND(AVG(i.on_hand_qty), 1) as avg_inventory,
    SUM(CASE WHEN i.overstock_flag THEN 1 ELSE 0 END) as overstock_events,
    ROUND(100.0 * SUM(CASE WHEN i.overstock_flag THEN 1 ELSE 0 END) / COUNT(*), 2) as overstock_rate_pct,
    SUM(i.carrying_cost_daily) as total_carrying_cost
FROM dim_products p
LEFT JOIN fact_inventory i ON p.sku_id = i.sku_id
GROUP BY p.category
ORDER BY total_carrying_cost DESC;

-- SKUs with excessive weeks of supply (>8 weeks)
SELECT 
    p.sku_id,
    p.product_name,
    p.category,
    ROUND(AVG(i.on_hand_qty), 1) as avg_inventory,
    ROUND(AVG(s.units_sold), 1) as avg_daily_demand,
    CASE 
        WHEN AVG(s.units_sold) > 0 
        THEN ROUND(AVG(i.on_hand_qty) / AVG(s.units_sold) / 7, 1)
        ELSE NULL 
    END as weeks_of_supply,
    SUM(i.carrying_cost_daily) as total_carrying_cost,
    p.unit_price * AVG(i.on_hand_qty) as tied_up_capital
FROM dim_products p
LEFT JOIN fact_inventory i ON p.sku_id = i.sku_id
LEFT JOIN fact_sales s ON p.sku_id = s.sku_id AND i.date = s.date
GROUP BY p.sku_id, p.product_name, p.category, p.unit_price
HAVING AVG(s.units_sold) > 0 AND AVG(i.on_hand_qty) / AVG(s.units_sold) / 7 > 8
ORDER BY weeks_of_supply DESC
LIMIT 30;

-- Monthly overstock trend
SELECT 
    DATE_TRUNC('month', i.date) as month,
    SUM(CASE WHEN i.overstock_flag THEN 1 ELSE 0 END) as overstock_events,
    COUNT(*) as total_sku_days,
    ROUND(100.0 * SUM(CASE WHEN i.overstock_flag THEN 1 ELSE 0 END) / COUNT(*), 2) as overstock_rate_pct,
    SUM(i.carrying_cost_daily) as monthly_carrying_cost
FROM fact_inventory i
GROUP BY DATE_TRUNC('month', i.date)
ORDER BY month;
