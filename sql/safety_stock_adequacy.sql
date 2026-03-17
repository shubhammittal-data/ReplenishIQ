-- Safety Stock Adequacy Analysis
-- Identifies SKUs where safety stock is too low (causing stockouts) or too high (excess inventory)

-- Safety stock analysis by SKU
SELECT 
    p.sku_id,
    p.product_name,
    p.category,
    p.safety_stock,
    p.reorder_point,
    ROUND(AVG(i.on_hand_qty), 1) as avg_inventory,
    ROUND(AVG(s.units_sold), 1) as avg_daily_demand,
    SUM(CASE WHEN i.stockout_flag THEN 1 ELSE 0 END) as stockout_days,
    ROUND(100.0 * SUM(CASE WHEN i.stockout_flag THEN 1 ELSE 0 END) / COUNT(*), 2) as stockout_rate_pct,
    CASE 
        WHEN SUM(CASE WHEN i.stockout_flag THEN 1 ELSE 0 END) > 30 THEN 'Safety Stock Too Low'
        WHEN AVG(i.on_hand_qty) > p.max_stock_level * 1.5 THEN 'Safety Stock Too High'
        ELSE 'Adequate'
    END as safety_stock_status,
    CASE 
        WHEN AVG(s.units_sold) > 0 
        THEN ROUND(p.safety_stock / AVG(s.units_sold), 1)
        ELSE NULL 
    END as safety_stock_days_coverage
FROM dim_products p
LEFT JOIN fact_inventory i ON p.sku_id = i.sku_id
LEFT JOIN fact_sales s ON p.sku_id = s.sku_id AND i.date = s.date
GROUP BY p.sku_id, p.product_name, p.category, p.safety_stock, p.reorder_point, p.max_stock_level
ORDER BY stockout_days DESC;

-- SKUs with inadequate safety stock (high stockout rate)
SELECT 
    p.sku_id,
    p.product_name,
    p.category,
    p.safety_stock as current_safety_stock,
    ROUND(AVG(s.units_sold), 1) as avg_daily_demand,
    p.lead_time_days,
    SUM(CASE WHEN i.stockout_flag THEN 1 ELSE 0 END) as stockout_days,
    ROUND(100.0 * SUM(CASE WHEN i.stockout_flag THEN 1 ELSE 0 END) / COUNT(*), 2) as stockout_rate_pct,
    -- Recommended safety stock = 2 * std_dev * sqrt(lead_time)
    ROUND(2 * STDDEV(s.units_sold) * SQRT(p.lead_time_days), 0) as recommended_safety_stock
FROM dim_products p
LEFT JOIN fact_inventory i ON p.sku_id = i.sku_id
LEFT JOIN fact_sales s ON p.sku_id = s.sku_id AND i.date = s.date
GROUP BY p.sku_id, p.product_name, p.category, p.safety_stock, p.lead_time_days
HAVING SUM(CASE WHEN i.stockout_flag THEN 1 ELSE 0 END) > 20
ORDER BY stockout_days DESC
LIMIT 30;

-- SKUs with excessive safety stock (overstock risk)
SELECT 
    p.sku_id,
    p.product_name,
    p.category,
    p.safety_stock as current_safety_stock,
    ROUND(AVG(i.on_hand_qty), 1) as avg_inventory,
    p.max_stock_level,
    ROUND(AVG(s.units_sold), 1) as avg_daily_demand,
    CASE 
        WHEN AVG(s.units_sold) > 0 
        THEN ROUND(AVG(i.on_hand_qty) / AVG(s.units_sold), 1)
        ELSE NULL 
    END as days_of_supply,
    SUM(i.carrying_cost_daily) as total_carrying_cost
FROM dim_products p
LEFT JOIN fact_inventory i ON p.sku_id = i.sku_id
LEFT JOIN fact_sales s ON p.sku_id = s.sku_id AND i.date = s.date
GROUP BY p.sku_id, p.product_name, p.category, p.safety_stock, p.max_stock_level
HAVING AVG(i.on_hand_qty) > p.max_stock_level
ORDER BY total_carrying_cost DESC
LIMIT 30;
