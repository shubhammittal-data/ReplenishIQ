-- Exception Summary
-- Master query combining all exception flags and ranking SKUs by severity

-- Comprehensive exception summary
WITH stockout_stats AS (
    SELECT 
        sku_id,
        SUM(CASE WHEN stockout_flag THEN 1 ELSE 0 END) as stockout_days,
        ROUND(100.0 * SUM(CASE WHEN stockout_flag THEN 1 ELSE 0 END) / COUNT(*), 2) as stockout_rate
    FROM fact_inventory
    GROUP BY sku_id
),
overstock_stats AS (
    SELECT 
        sku_id,
        SUM(CASE WHEN overstock_flag THEN 1 ELSE 0 END) as overstock_days,
        ROUND(100.0 * SUM(CASE WHEN overstock_flag THEN 1 ELSE 0 END) / COUNT(*), 2) as overstock_rate,
        SUM(carrying_cost_daily) as total_carrying_cost
    FROM fact_inventory
    GROUP BY sku_id
),
inventory_stats AS (
    SELECT 
        i.sku_id,
        ROUND(AVG(i.on_hand_qty), 1) as avg_inventory,
        ROUND(100.0 * SUM(CASE WHEN i.instock_flag THEN 1 ELSE 0 END) / COUNT(*), 2) as instock_rate
    FROM fact_inventory i
    GROUP BY i.sku_id
),
sales_stats AS (
    SELECT 
        sku_id,
        SUM(units_sold) as total_units,
        SUM(revenue) as total_revenue,
        ROUND(AVG(units_sold), 1) as avg_daily_demand
    FROM fact_sales
    GROUP BY sku_id
)
SELECT 
    p.sku_id,
    p.product_name,
    p.category,
    p.supplier_id,
    p.slg_target * 100 as slg_target_pct,
    inv.instock_rate,
    st.stockout_days,
    st.stockout_rate,
    ov.overstock_days,
    ov.overstock_rate,
    ov.total_carrying_cost,
    ss.total_revenue,
    -- Exception flags
    CASE WHEN inv.instock_rate < p.slg_target * 100 THEN 1 ELSE 0 END as below_slg_flag,
    CASE WHEN st.stockout_days > 30 THEN 1 ELSE 0 END as high_stockout_flag,
    CASE WHEN ov.overstock_days > 100 THEN 1 ELSE 0 END as high_overstock_flag,
    -- Priority score (higher = more urgent)
    -- Stockouts weighted more heavily than overstock
    ROUND(
        (CASE WHEN inv.instock_rate < p.slg_target * 100 THEN 30 ELSE 0 END) +
        (st.stockout_rate * 2) +
        (ov.overstock_rate * 0.5) +
        (CASE WHEN ss.total_revenue > 50000 THEN 20 ELSE 0 END)  -- High revenue SKUs get priority
    , 1) as priority_score,
    -- Recommended action
    CASE 
        WHEN st.stockout_days > 50 THEN 'CRITICAL: Increase safety stock immediately'
        WHEN st.stockout_days > 30 THEN 'HIGH: Review and increase reorder point'
        WHEN inv.instock_rate < p.slg_target * 100 THEN 'MEDIUM: Adjust safety stock parameters'
        WHEN ov.overstock_days > 150 THEN 'LOW: Reduce max stock level'
        WHEN ov.overstock_days > 100 THEN 'LOW: Review ordering frequency'
        ELSE 'OK: No action needed'
    END as recommended_action
FROM dim_products p
LEFT JOIN stockout_stats st ON p.sku_id = st.sku_id
LEFT JOIN overstock_stats ov ON p.sku_id = ov.sku_id
LEFT JOIN inventory_stats inv ON p.sku_id = inv.sku_id
LEFT JOIN sales_stats ss ON p.sku_id = ss.sku_id
ORDER BY priority_score DESC;

-- Top 20 exceptions needing immediate attention
WITH exception_data AS (
    SELECT 
        p.sku_id,
        p.product_name,
        p.category,
        ROUND(100.0 * SUM(CASE WHEN i.instock_flag THEN 1 ELSE 0 END) / COUNT(*), 2) as instock_rate,
        SUM(CASE WHEN i.stockout_flag THEN 1 ELSE 0 END) as stockout_days,
        SUM(CASE WHEN i.overstock_flag THEN 1 ELSE 0 END) as overstock_days,
        SUM(s.revenue) as total_revenue,
        p.slg_target
    FROM dim_products p
    LEFT JOIN fact_inventory i ON p.sku_id = i.sku_id
    LEFT JOIN fact_sales s ON p.sku_id = s.sku_id AND i.date = s.date
    GROUP BY p.sku_id, p.product_name, p.category, p.slg_target
)
SELECT 
    sku_id,
    product_name,
    category,
    instock_rate,
    slg_target * 100 as slg_target_pct,
    stockout_days,
    overstock_days,
    total_revenue,
    CASE 
        WHEN stockout_days > 50 THEN 'Stockout Crisis'
        WHEN instock_rate < slg_target * 100 THEN 'Below SLG'
        WHEN overstock_days > 150 THEN 'Severe Overstock'
        ELSE 'Review Needed'
    END as exception_type
FROM exception_data
WHERE stockout_days > 30 OR instock_rate < slg_target * 100 OR overstock_days > 100
ORDER BY stockout_days DESC, (slg_target * 100 - instock_rate) DESC
LIMIT 20;

-- Exception count summary by category
SELECT 
    p.category,
    COUNT(DISTINCT p.sku_id) as total_skus,
    SUM(CASE WHEN inv.instock_rate < p.slg_target * 100 THEN 1 ELSE 0 END) as below_slg_count,
    SUM(CASE WHEN st.stockout_days > 30 THEN 1 ELSE 0 END) as high_stockout_count,
    SUM(CASE WHEN ov.overstock_days > 100 THEN 1 ELSE 0 END) as high_overstock_count
FROM dim_products p
LEFT JOIN (
    SELECT sku_id, ROUND(100.0 * SUM(CASE WHEN instock_flag THEN 1 ELSE 0 END) / COUNT(*), 2) as instock_rate
    FROM fact_inventory GROUP BY sku_id
) inv ON p.sku_id = inv.sku_id
LEFT JOIN (
    SELECT sku_id, SUM(CASE WHEN stockout_flag THEN 1 ELSE 0 END) as stockout_days
    FROM fact_inventory GROUP BY sku_id
) st ON p.sku_id = st.sku_id
LEFT JOIN (
    SELECT sku_id, SUM(CASE WHEN overstock_flag THEN 1 ELSE 0 END) as overstock_days
    FROM fact_inventory GROUP BY sku_id
) ov ON p.sku_id = ov.sku_id
GROUP BY p.category
ORDER BY high_stockout_count DESC;
