-- Supplier Performance Analysis
-- Evaluates lead time variance, fill rates, and on-time delivery

-- Overall supplier performance
SELECT 
    s.supplier_id,
    s.supplier_name,
    s.avg_lead_time as expected_lead_time,
    s.lead_time_variance as expected_variance,
    ROUND(AVG(o.lead_time_actual), 1) as actual_avg_lead_time,
    ROUND(STDDEV(o.lead_time_actual), 2) as actual_lead_time_stddev,
    s.fill_rate as expected_fill_rate,
    ROUND(AVG(o.fill_rate_actual), 4) as actual_fill_rate,
    s.on_time_delivery_rate as expected_otd,
    ROUND(100.0 * SUM(CASE WHEN o.actual_delivery_date <= o.expected_delivery_date THEN 1 ELSE 0 END) / COUNT(*), 2) as actual_otd_pct,
    COUNT(*) as total_orders
FROM dim_suppliers s
LEFT JOIN fact_replenishment_orders o ON s.supplier_id = o.supplier_id
GROUP BY s.supplier_id, s.supplier_name, s.avg_lead_time, s.lead_time_variance, s.fill_rate, s.on_time_delivery_rate
ORDER BY actual_otd_pct DESC;

-- Supplier performance by month (trend)
SELECT 
    o.supplier_id,
    s.supplier_name,
    DATE_TRUNC('month', o.order_date) as month,
    COUNT(*) as orders,
    ROUND(AVG(o.lead_time_actual), 1) as avg_lead_time,
    ROUND(AVG(o.fill_rate_actual), 4) as avg_fill_rate,
    ROUND(100.0 * SUM(CASE WHEN o.actual_delivery_date <= o.expected_delivery_date THEN 1 ELSE 0 END) / COUNT(*), 2) as otd_pct
FROM fact_replenishment_orders o
JOIN dim_suppliers s ON o.supplier_id = s.supplier_id
GROUP BY o.supplier_id, s.supplier_name, DATE_TRUNC('month', o.order_date)
ORDER BY o.supplier_id, month;

-- Late deliveries analysis
SELECT 
    o.supplier_id,
    s.supplier_name,
    o.order_id,
    o.sku_id,
    p.product_name,
    o.order_date,
    o.expected_delivery_date,
    o.actual_delivery_date,
    o.actual_delivery_date - o.expected_delivery_date as days_late,
    o.lead_time_actual
FROM fact_replenishment_orders o
JOIN dim_suppliers s ON o.supplier_id = s.supplier_id
JOIN dim_products p ON o.sku_id = p.sku_id
WHERE o.actual_delivery_date > o.expected_delivery_date
ORDER BY days_late DESC
LIMIT 50;

-- Supplier reliability score (composite metric)
SELECT 
    s.supplier_id,
    s.supplier_name,
    ROUND(AVG(o.fill_rate_actual) * 100, 1) as fill_rate_score,
    ROUND(100.0 * SUM(CASE WHEN o.actual_delivery_date <= o.expected_delivery_date THEN 1 ELSE 0 END) / COUNT(*), 1) as otd_score,
    ROUND(100 - (STDDEV(o.lead_time_actual) / NULLIF(AVG(o.lead_time_actual), 0) * 100), 1) as consistency_score,
    ROUND(
        (AVG(o.fill_rate_actual) * 100 * 0.3) + 
        (100.0 * SUM(CASE WHEN o.actual_delivery_date <= o.expected_delivery_date THEN 1 ELSE 0 END) / COUNT(*) * 0.4) +
        ((100 - COALESCE(STDDEV(o.lead_time_actual) / NULLIF(AVG(o.lead_time_actual), 0) * 100, 0)) * 0.3)
    , 1) as overall_reliability_score
FROM dim_suppliers s
LEFT JOIN fact_replenishment_orders o ON s.supplier_id = o.supplier_id
GROUP BY s.supplier_id, s.supplier_name
ORDER BY overall_reliability_score DESC;
