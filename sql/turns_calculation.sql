-- Inventory Turns Calculation
-- Turns = Annual Sales / Average Inventory
-- Higher turns = more efficient inventory management

-- Inventory turns by SKU
SELECT 
    p.sku_id,
    p.product_name,
    p.category,
    p.unit_price,
    SUM(s.units_sold) as total_units_sold,
    ROUND(AVG(i.on_hand_qty), 1) as avg_inventory,
    CASE 
        WHEN AVG(i.on_hand_qty) > 0 
        THEN ROUND(SUM(s.units_sold)::numeric / AVG(i.on_hand_qty), 2)
        ELSE 0 
    END as inventory_turns,
    CASE 
        WHEN AVG(i.on_hand_qty) > 0 AND SUM(s.units_sold) > 0
        THEN ROUND(365.0 / (SUM(s.units_sold)::numeric / AVG(i.on_hand_qty)), 1)
        ELSE NULL 
    END as days_to_turn
FROM dim_products p
LEFT JOIN fact_sales s ON p.sku_id = s.sku_id
LEFT JOIN fact_inventory i ON p.sku_id = i.sku_id
GROUP BY p.sku_id, p.product_name, p.category, p.unit_price
ORDER BY inventory_turns DESC;

-- Inventory turns by category
SELECT 
    p.category,
    SUM(s.units_sold) as total_units_sold,
    ROUND(AVG(i.on_hand_qty), 1) as avg_inventory,
    CASE 
        WHEN AVG(i.on_hand_qty) > 0 
        THEN ROUND(SUM(s.units_sold)::numeric / AVG(i.on_hand_qty), 2)
        ELSE 0 
    END as inventory_turns
FROM dim_products p
LEFT JOIN fact_sales s ON p.sku_id = s.sku_id
LEFT JOIN fact_inventory i ON p.sku_id = i.sku_id
GROUP BY p.category
ORDER BY inventory_turns DESC;

-- Monthly inventory turns trend
SELECT 
    DATE_TRUNC('month', s.date) as month,
    SUM(s.units_sold) as monthly_sales,
    ROUND(AVG(i.on_hand_qty), 1) as avg_inventory,
    CASE 
        WHEN AVG(i.on_hand_qty) > 0 
        THEN ROUND(SUM(s.units_sold)::numeric / AVG(i.on_hand_qty), 2)
        ELSE 0 
    END as monthly_turns
FROM fact_sales s
JOIN fact_inventory i ON s.sku_id = i.sku_id AND s.date = i.date
GROUP BY DATE_TRUNC('month', s.date)
ORDER BY month;

-- Slow movers (low turns - potential overstock)
SELECT 
    p.sku_id,
    p.product_name,
    p.category,
    SUM(s.units_sold) as total_units_sold,
    ROUND(AVG(i.on_hand_qty), 1) as avg_inventory,
    CASE 
        WHEN AVG(i.on_hand_qty) > 0 
        THEN ROUND(SUM(s.units_sold)::numeric / AVG(i.on_hand_qty), 2)
        ELSE 0 
    END as inventory_turns
FROM dim_products p
LEFT JOIN fact_sales s ON p.sku_id = s.sku_id
LEFT JOIN fact_inventory i ON p.sku_id = i.sku_id
GROUP BY p.sku_id, p.product_name, p.category
HAVING AVG(i.on_hand_qty) > 0
ORDER BY inventory_turns ASC
LIMIT 20;
