-- Parameter Evaluation
-- Evaluates if min/max, reorder points, and other parameters are set correctly

-- Reorder point evaluation
SELECT 
    p.sku_id,
    p.product_name,
    p.category,
    p.reorder_point,
    p.safety_stock,
    p.lead_time_days,
    ROUND(AVG(s.units_sold), 1) as avg_daily_demand,
    ROUND(AVG(s.units_sold) * p.lead_time_days + p.safety_stock, 0) as calculated_rop,
    p.reorder_point - ROUND(AVG(s.units_sold) * p.lead_time_days + p.safety_stock, 0) as rop_difference,
    CASE 
        WHEN p.reorder_point < AVG(s.units_sold) * p.lead_time_days THEN 'ROP Too Low - Stockout Risk'
        WHEN p.reorder_point > AVG(s.units_sold) * p.lead_time_days * 2 + p.safety_stock THEN 'ROP Too High - Overstock Risk'
        ELSE 'ROP Adequate'
    END as rop_status
FROM dim_products p
LEFT JOIN fact_sales s ON p.sku_id = s.sku_id
GROUP BY p.sku_id, p.product_name, p.category, p.reorder_point, p.safety_stock, p.lead_time_days
ORDER BY ABS(p.reorder_point - ROUND(AVG(s.units_sold) * p.lead_time_days + p.safety_stock, 0)) DESC;

-- Min/Max evaluation
SELECT 
    p.sku_id,
    p.product_name,
    p.category,
    p.min_order_qty,
    p.max_stock_level,
    p.safety_stock,
    ROUND(AVG(i.on_hand_qty), 1) as avg_inventory,
    ROUND(AVG(s.units_sold), 1) as avg_daily_demand,
    CASE 
        WHEN AVG(s.units_sold) > 0 
        THEN ROUND(p.max_stock_level / AVG(s.units_sold), 1)
        ELSE NULL 
    END as max_days_coverage,
    CASE 
        WHEN p.max_stock_level < p.safety_stock * 2 THEN 'Max Too Low'
        WHEN AVG(s.units_sold) > 0 AND p.max_stock_level / AVG(s.units_sold) > 90 THEN 'Max Too High (>90 days)'
        ELSE 'Max Adequate'
    END as max_status,
    CASE 
        WHEN AVG(s.units_sold) > 0 AND p.min_order_qty < AVG(s.units_sold) * 3 THEN 'MOQ Too Low'
        WHEN AVG(s.units_sold) > 0 AND p.min_order_qty > AVG(s.units_sold) * 30 THEN 'MOQ Too High'
        ELSE 'MOQ Adequate'
    END as moq_status
FROM dim_products p
LEFT JOIN fact_inventory i ON p.sku_id = i.sku_id
LEFT JOIN fact_sales s ON p.sku_id = s.sku_id
GROUP BY p.sku_id, p.product_name, p.category, p.min_order_qty, p.max_stock_level, p.safety_stock
ORDER BY p.sku_id;

-- Order policy effectiveness
SELECT 
    p.order_policy,
    COUNT(DISTINCT p.sku_id) as sku_count,
    ROUND(100.0 * SUM(CASE WHEN i.instock_flag THEN 1 ELSE 0 END) / COUNT(*), 2) as avg_instock_rate,
    ROUND(100.0 * SUM(CASE WHEN i.stockout_flag THEN 1 ELSE 0 END) / COUNT(*), 2) as avg_stockout_rate,
    ROUND(100.0 * SUM(CASE WHEN i.overstock_flag THEN 1 ELSE 0 END) / COUNT(*), 2) as avg_overstock_rate,
    SUM(i.carrying_cost_daily) as total_carrying_cost
FROM dim_products p
LEFT JOIN fact_inventory i ON p.sku_id = i.sku_id
GROUP BY p.order_policy
ORDER BY avg_instock_rate DESC;

-- Parameters needing adjustment (combined view)
SELECT 
    p.sku_id,
    p.product_name,
    p.category,
    p.order_policy,
    ROUND(100.0 * SUM(CASE WHEN i.stockout_flag THEN 1 ELSE 0 END) / COUNT(*), 2) as stockout_rate,
    ROUND(100.0 * SUM(CASE WHEN i.overstock_flag THEN 1 ELSE 0 END) / COUNT(*), 2) as overstock_rate,
    CASE 
        WHEN SUM(CASE WHEN i.stockout_flag THEN 1 ELSE 0 END) > 30 THEN 'Increase Safety Stock/ROP'
        WHEN SUM(CASE WHEN i.overstock_flag THEN 1 ELSE 0 END) > 100 THEN 'Decrease Max/Safety Stock'
        ELSE 'No Change Needed'
    END as recommended_action
FROM dim_products p
LEFT JOIN fact_inventory i ON p.sku_id = i.sku_id
GROUP BY p.sku_id, p.product_name, p.category, p.order_policy
HAVING SUM(CASE WHEN i.stockout_flag THEN 1 ELSE 0 END) > 30 
    OR SUM(CASE WHEN i.overstock_flag THEN 1 ELSE 0 END) > 100
ORDER BY stockout_rate DESC, overstock_rate DESC;
