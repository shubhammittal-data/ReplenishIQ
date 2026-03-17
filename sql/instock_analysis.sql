-- InStock Analysis
-- Calculates in-stock rate by SKU, category, and month
-- In-stock rate = % of days where inventory > 0

-- Overall in-stock rate by SKU
SELECT 
    p.sku_id,
    p.product_name,
    p.category,
    COUNT(*) as total_days,
    SUM(CASE WHEN i.instock_flag THEN 1 ELSE 0 END) as instock_days,
    ROUND(100.0 * SUM(CASE WHEN i.instock_flag THEN 1 ELSE 0 END) / COUNT(*), 2) as instock_rate_pct,
    p.slg_target * 100 as slg_target_pct,
    CASE 
        WHEN ROUND(100.0 * SUM(CASE WHEN i.instock_flag THEN 1 ELSE 0 END) / COUNT(*), 2) >= p.slg_target * 100 
        THEN 'Meeting SLG'
        ELSE 'Below SLG'
    END as slg_status
FROM fact_inventory i
JOIN dim_products p ON i.sku_id = p.sku_id
GROUP BY p.sku_id, p.product_name, p.category, p.slg_target
ORDER BY instock_rate_pct ASC;

-- In-stock rate by category
SELECT 
    p.category,
    COUNT(*) as total_days,
    SUM(CASE WHEN i.instock_flag THEN 1 ELSE 0 END) as instock_days,
    ROUND(100.0 * SUM(CASE WHEN i.instock_flag THEN 1 ELSE 0 END) / COUNT(*), 2) as instock_rate_pct
FROM fact_inventory i
JOIN dim_products p ON i.sku_id = p.sku_id
GROUP BY p.category
ORDER BY instock_rate_pct ASC;

-- In-stock rate by month (trend analysis)
SELECT 
    DATE_TRUNC('month', i.date) as month,
    COUNT(*) as total_days,
    SUM(CASE WHEN i.instock_flag THEN 1 ELSE 0 END) as instock_days,
    ROUND(100.0 * SUM(CASE WHEN i.instock_flag THEN 1 ELSE 0 END) / COUNT(*), 2) as instock_rate_pct
FROM fact_inventory i
GROUP BY DATE_TRUNC('month', i.date)
ORDER BY month;

-- SKUs with worst in-stock performance (bottom 20)
SELECT 
    p.sku_id,
    p.product_name,
    p.category,
    ROUND(100.0 * SUM(CASE WHEN i.instock_flag THEN 1 ELSE 0 END) / COUNT(*), 2) as instock_rate_pct,
    SUM(CASE WHEN i.stockout_flag THEN 1 ELSE 0 END) as stockout_days,
    p.slg_target * 100 as slg_target_pct
FROM fact_inventory i
JOIN dim_products p ON i.sku_id = p.sku_id
GROUP BY p.sku_id, p.product_name, p.category, p.slg_target
ORDER BY instock_rate_pct ASC
LIMIT 20;
