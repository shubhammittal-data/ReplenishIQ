-- Stockout Frequency Analysis
-- Counts stockout events per SKU per month and identifies patterns

-- Stockout frequency by SKU (overall)
SELECT 
    p.sku_id,
    p.product_name,
    p.category,
    p.supplier_id,
    COUNT(*) as total_days,
    SUM(CASE WHEN i.stockout_flag THEN 1 ELSE 0 END) as stockout_days,
    ROUND(100.0 * SUM(CASE WHEN i.stockout_flag THEN 1 ELSE 0 END) / COUNT(*), 2) as stockout_rate_pct,
    p.slg_target * 100 as slg_target_pct,
    ROUND((1 - p.slg_target) * 100, 2) as allowed_stockout_pct,
    CASE 
        WHEN ROUND(100.0 * SUM(CASE WHEN i.stockout_flag THEN 1 ELSE 0 END) / COUNT(*), 2) > (1 - p.slg_target) * 100
        THEN 'Exceeds Allowed Stockout'
        ELSE 'Within Tolerance'
    END as status
FROM fact_inventory i
JOIN dim_products p ON i.sku_id = p.sku_id
GROUP BY p.sku_id, p.product_name, p.category, p.supplier_id, p.slg_target
ORDER BY stockout_days DESC;

-- Stockout frequency by month (trend)
SELECT 
    DATE_TRUNC('month', i.date) as month,
    COUNT(DISTINCT i.sku_id) as total_skus,
    SUM(CASE WHEN i.stockout_flag THEN 1 ELSE 0 END) as stockout_events,
    COUNT(*) as total_sku_days,
    ROUND(100.0 * SUM(CASE WHEN i.stockout_flag THEN 1 ELSE 0 END) / COUNT(*), 2) as stockout_rate_pct
FROM fact_inventory i
GROUP BY DATE_TRUNC('month', i.date)
ORDER BY month;

-- Stockout frequency by category
SELECT 
    p.category,
    COUNT(DISTINCT p.sku_id) as sku_count,
    SUM(CASE WHEN i.stockout_flag THEN 1 ELSE 0 END) as stockout_events,
    COUNT(*) as total_sku_days,
    ROUND(100.0 * SUM(CASE WHEN i.stockout_flag THEN 1 ELSE 0 END) / COUNT(*), 2) as stockout_rate_pct
FROM fact_inventory i
JOIN dim_products p ON i.sku_id = p.sku_id
GROUP BY p.category
ORDER BY stockout_rate_pct DESC;

-- Consecutive stockout days (most severe stockouts)
WITH stockout_runs AS (
    SELECT 
        sku_id,
        date,
        stockout_flag,
        SUM(CASE WHEN NOT stockout_flag THEN 1 ELSE 0 END) OVER (PARTITION BY sku_id ORDER BY date) as grp
    FROM fact_inventory
),
run_lengths AS (
    SELECT 
        sku_id,
        MIN(date) as stockout_start,
        MAX(date) as stockout_end,
        COUNT(*) as consecutive_days
    FROM stockout_runs
    WHERE stockout_flag = true
    GROUP BY sku_id, grp
)
SELECT 
    r.sku_id,
    p.product_name,
    p.category,
    r.stockout_start,
    r.stockout_end,
    r.consecutive_days
FROM run_lengths r
JOIN dim_products p ON r.sku_id = p.sku_id
WHERE r.consecutive_days >= 3
ORDER BY r.consecutive_days DESC, r.stockout_start
LIMIT 50;
