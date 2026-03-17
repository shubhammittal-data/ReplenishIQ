"""
ReplenishIQ Professional Dashboard v2
Creates a comprehensive, visually appealing dashboard using Plotly.
"""

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_data():
    """Load all data files."""
    project_root = get_project_root()
    data_dir = os.path.join(project_root, 'data', 'processed')
    tableau_dir = os.path.join(project_root, 'tableau')
    
    data = {}
    data['products'] = pd.read_csv(os.path.join(data_dir, 'dim_products.csv'))
    data['sales'] = pd.read_csv(os.path.join(data_dir, 'fact_sales.csv'))
    data['inventory'] = pd.read_csv(os.path.join(data_dir, 'fact_inventory.csv'))
    data['suppliers'] = pd.read_csv(os.path.join(data_dir, 'dim_suppliers.csv'))
    data['orders'] = pd.read_csv(os.path.join(data_dir, 'fact_replenishment_orders.csv'))
    data['clusters'] = pd.read_csv(os.path.join(tableau_dir, 'sku_clusters.csv'))
    data['alerts'] = pd.read_csv(os.path.join(tableau_dir, 'exception_dashboard.csv'))
    
    # Convert dates
    data['sales']['date'] = pd.to_datetime(data['sales']['date'])
    data['inventory']['date'] = pd.to_datetime(data['inventory']['date'])
    
    return data


def create_kpi_section(data):
    """Create KPI cards section."""
    sales = data['sales']
    inventory = data['inventory']
    products = data['products']
    alerts = data['alerts']
    
    total_revenue = sales['revenue'].sum()
    total_units = sales['units_sold'].sum()
    instock_rate = inventory['instock_flag'].mean() * 100
    stockout_rate = inventory['stockout_flag'].mean() * 100
    sku_count = len(products)
    critical_alerts = len(alerts[alerts['priority_label'] == 'CRITICAL'])
    
    fig = make_subplots(
        rows=1, cols=6,
        specs=[[{"type": "indicator"}]*6],
        horizontal_spacing=0.02
    )
    
    # KPI 1: Revenue
    fig.add_trace(go.Indicator(
        mode="number",
        value=total_revenue,
        title={"text": "<b>Total Revenue</b>", "font": {"size": 14, "color": "#333"}},
        number={"prefix": "$", "font": {"size": 32, "color": "#1f77b4"}, "valueformat": ",.0f"},
    ), row=1, col=1)
    
    # KPI 2: Units Sold
    fig.add_trace(go.Indicator(
        mode="number",
        value=total_units,
        title={"text": "<b>Units Sold</b>", "font": {"size": 14, "color": "#333"}},
        number={"font": {"size": 32, "color": "#2ca02c"}, "valueformat": ",.0f"},
    ), row=1, col=2)
    
    # KPI 3: In-Stock Rate
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=instock_rate,
        title={"text": "<b>In-Stock Rate</b>", "font": {"size": 14, "color": "#333"}},
        number={"suffix": "%", "font": {"size": 24}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1},
            'bar': {'color': "#2ca02c" if instock_rate >= 90 else "#ff7f0e" if instock_rate >= 80 else "#d62728"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "#ccc",
            'threshold': {'line': {'color': "black", 'width': 3}, 'thickness': 0.8, 'value': 95}
        },
    ), row=1, col=3)
    
    # KPI 4: Stockout Rate
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=stockout_rate,
        title={"text": "<b>Stockout Rate</b>", "font": {"size": 14, "color": "#333"}},
        number={"suffix": "%", "font": {"size": 24}},
        gauge={
            'axis': {'range': [0, 50], 'tickwidth': 1},
            'bar': {'color': "#d62728" if stockout_rate > 15 else "#ff7f0e" if stockout_rate > 10 else "#2ca02c"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "#ccc",
        },
    ), row=1, col=4)
    
    # KPI 5: Active SKUs
    fig.add_trace(go.Indicator(
        mode="number",
        value=sku_count,
        title={"text": "<b>Active SKUs</b>", "font": {"size": 14, "color": "#333"}},
        number={"font": {"size": 32, "color": "#9467bd"}},
    ), row=1, col=5)
    
    # KPI 6: Critical Alerts
    fig.add_trace(go.Indicator(
        mode="number+delta",
        value=critical_alerts,
        title={"text": "<b>Critical Alerts</b>", "font": {"size": 14, "color": "#333"}},
        number={"font": {"size": 32, "color": "#d62728"}},
        delta={'reference': 0, 'increasing': {'color': "#d62728"}},
    ), row=1, col=6)
    
    fig.update_layout(
        height=180,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor='white',
    )
    
    return fig


def create_revenue_chart(data):
    """Create revenue trend chart."""
    sales = data['sales'].copy()
    sales['month'] = sales['date'].dt.to_period('M').astype(str)
    
    monthly = sales.groupby('month').agg({
        'revenue': 'sum',
        'units_sold': 'sum'
    }).reset_index()
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(
        go.Bar(
            x=monthly['month'],
            y=monthly['revenue'],
            name="Revenue",
            marker_color='#1f77b4',
            opacity=0.8
        ),
        secondary_y=False
    )
    
    fig.add_trace(
        go.Scatter(
            x=monthly['month'],
            y=monthly['units_sold'],
            name="Units Sold",
            line=dict(color='#ff7f0e', width=3),
            mode='lines+markers',
            marker=dict(size=8)
        ),
        secondary_y=True
    )
    
    fig.update_layout(
        title={"text": "<b>Monthly Revenue & Sales Volume</b>", "font": {"size": 16}},
        xaxis_title="Month",
        height=320,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=60, r=60, t=60, b=40),
        paper_bgcolor='white',
        plot_bgcolor='#f8f9fa',
    )
    
    fig.update_yaxes(title_text="Revenue ($)", secondary_y=False, gridcolor='#e0e0e0')
    fig.update_yaxes(title_text="Units Sold", secondary_y=True)
    fig.update_xaxes(gridcolor='#e0e0e0')
    
    return fig


def create_category_chart(data):
    """Create category performance chart."""
    sales = data['sales'].copy()
    products = data['products']
    
    # Merge to get category
    sales_cat = sales.merge(products[['sku_id', 'category']], on='sku_id', how='left')
    
    # Check if category column exists after merge
    if 'category' not in sales_cat.columns:
        # Try category_y or category_x
        if 'category_y' in sales_cat.columns:
            sales_cat['category'] = sales_cat['category_y']
        elif 'category_x' in sales_cat.columns:
            sales_cat['category'] = sales_cat['category_x']
    
    category_totals = sales_cat.groupby('category').agg({
        'revenue': 'sum',
        'units_sold': 'sum'
    }).reset_index().sort_values('revenue', ascending=True)
    
    colors = px.colors.qualitative.Set2[:len(category_totals)]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=category_totals['category'],
        x=category_totals['revenue'],
        orientation='h',
        marker_color=colors,
        text=category_totals['revenue'].apply(lambda x: f'${x/1e6:.1f}M'),
        textposition='outside',
        textfont=dict(size=11)
    ))
    
    fig.update_layout(
        title={"text": "<b>Revenue by Category</b>", "font": {"size": 16}},
        xaxis_title="Total Revenue ($)",
        height=320,
        margin=dict(l=120, r=80, t=60, b=40),
        paper_bgcolor='white',
        plot_bgcolor='#f8f9fa',
    )
    fig.update_xaxes(gridcolor='#e0e0e0')
    
    return fig


def create_instock_trend(data):
    """Create in-stock rate trend."""
    inventory = data['inventory'].copy()
    products = data['products']
    
    # Merge to get category
    inv_cat = inventory.merge(products[['sku_id', 'category']], on='sku_id', how='left')
    
    # Handle column naming
    if 'category' not in inv_cat.columns:
        if 'category_y' in inv_cat.columns:
            inv_cat['category'] = inv_cat['category_y']
        elif 'category_x' in inv_cat.columns:
            inv_cat['category'] = inv_cat['category_x']
    
    inv_cat['month'] = inv_cat['date'].dt.to_period('M').astype(str)
    
    monthly_instock = inv_cat.groupby(['month', 'category']).agg({
        'instock_flag': 'mean'
    }).reset_index()
    monthly_instock['instock_pct'] = monthly_instock['instock_flag'] * 100
    
    fig = px.line(
        monthly_instock,
        x='month',
        y='instock_pct',
        color='category',
        markers=True,
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    
    # Add 95% target line
    fig.add_hline(y=95, line_dash="dash", line_color="red", 
                  annotation_text="95% Target", annotation_position="right")
    
    fig.update_layout(
        title={"text": "<b>In-Stock Rate Trend by Category</b>", "font": {"size": 16}},
        xaxis_title="Month",
        yaxis_title="In-Stock Rate (%)",
        yaxis_range=[75, 102],
        height=320,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=60, r=20, t=80, b=40),
        paper_bgcolor='white',
        plot_bgcolor='#f8f9fa',
    )
    fig.update_xaxes(gridcolor='#e0e0e0')
    fig.update_yaxes(gridcolor='#e0e0e0')
    
    return fig


def create_alert_charts(data):
    """Create alert summary charts."""
    alerts = data['alerts'].copy()
    
    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "pie"}, {"type": "bar"}]],
        subplot_titles=("<b>Alerts by Priority</b>", "<b>Alerts by Type</b>"),
        horizontal_spacing=0.12
    )
    
    # Priority pie
    priority_counts = alerts['priority_label'].value_counts()
    colors_priority = {'CRITICAL': '#d62728', 'HIGH': '#ff7f0e', 'MEDIUM': '#ffd700', 'LOW': '#2ca02c'}
    
    fig.add_trace(
        go.Pie(
            labels=priority_counts.index,
            values=priority_counts.values,
            marker_colors=[colors_priority.get(p, '#999') for p in priority_counts.index],
            hole=0.45,
            textinfo='label+value',
            textfont=dict(size=11)
        ),
        row=1, col=1
    )
    
    # Type bar
    type_counts = alerts['alert_type'].value_counts().sort_values()
    
    fig.add_trace(
        go.Bar(
            x=type_counts.values,
            y=type_counts.index,
            orientation='h',
            marker_color='#1f77b4',
            text=type_counts.values,
            textposition='outside'
        ),
        row=1, col=2
    )
    
    fig.update_layout(
        height=320,
        showlegend=False,
        margin=dict(l=20, r=40, t=60, b=40),
        paper_bgcolor='white',
    )
    
    return fig


def create_cluster_chart(data):
    """Create SKU cluster scatter plot."""
    clusters = data['clusters'].copy()
    
    # Clean data
    clusters['avg_daily_demand'] = pd.to_numeric(clusters['avg_daily_demand'], errors='coerce').fillna(0)
    clusters['total_revenue'] = pd.to_numeric(clusters['total_revenue'], errors='coerce').fillna(0)
    
    color_map = {'A': '#2ca02c', 'B': '#1f77b4', 'C': '#ff7f0e', 'D': '#d62728'}
    
    fig = px.scatter(
        clusters,
        x='avg_daily_demand',
        y='total_revenue',
        color='cluster_label',
        hover_data=['sku_id', 'category'],
        color_discrete_map=color_map,
        opacity=0.7
    )
    
    fig.update_traces(marker=dict(size=10, line=dict(width=1, color='white')))
    
    fig.update_layout(
        title={"text": "<b>SKU Segmentation (A/B/C/D Clusters)</b>", "font": {"size": 16}},
        xaxis_title="Average Daily Demand (units)",
        yaxis_title="Total Revenue ($)",
        height=380,
        legend_title="Cluster",
        margin=dict(l=60, r=20, t=60, b=40),
        paper_bgcolor='white',
        plot_bgcolor='#f8f9fa',
    )
    fig.update_xaxes(gridcolor='#e0e0e0')
    fig.update_yaxes(gridcolor='#e0e0e0')
    
    return fig


def create_supplier_chart(data):
    """Create supplier performance chart."""
    suppliers = data['suppliers'].copy()
    
    # Calculate metrics
    metrics_df = pd.DataFrame({
        'Supplier': suppliers['supplier_name'],
        'Fill Rate': suppliers['fill_rate'] * 100,
        'On-Time Rate': suppliers['on_time_delivery_rate'] * 100,
        'Lead Time': suppliers['avg_lead_time']
    })
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Fill Rate (%)',
        x=metrics_df['Supplier'],
        y=metrics_df['Fill Rate'],
        marker_color='#1f77b4'
    ))
    
    fig.add_trace(go.Bar(
        name='On-Time Rate (%)',
        x=metrics_df['Supplier'],
        y=metrics_df['On-Time Rate'],
        marker_color='#2ca02c'
    ))
    
    fig.update_layout(
        title={"text": "<b>Supplier Performance Comparison</b>", "font": {"size": 16}},
        xaxis_title="Supplier",
        yaxis_title="Rate (%)",
        barmode='group',
        height=320,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=60, r=20, t=80, b=80),
        paper_bgcolor='white',
        plot_bgcolor='#f8f9fa',
    )
    fig.update_xaxes(gridcolor='#e0e0e0', tickangle=45)
    fig.update_yaxes(gridcolor='#e0e0e0')
    
    return fig


def create_stockout_heatmap(data):
    """Create stockout heatmap."""
    inventory = data['inventory'].copy()
    products = data['products']
    
    inv_cat = inventory.merge(products[['sku_id', 'category']], on='sku_id', how='left')
    
    # Handle column naming
    if 'category' not in inv_cat.columns:
        if 'category_y' in inv_cat.columns:
            inv_cat['category'] = inv_cat['category_y']
        elif 'category_x' in inv_cat.columns:
            inv_cat['category'] = inv_cat['category_x']
    
    inv_cat['month'] = inv_cat['date'].dt.strftime('%Y-%m')
    
    heatmap_data = inv_cat.groupby(['category', 'month'])['stockout_flag'].sum().reset_index()
    heatmap_pivot = heatmap_data.pivot(index='category', columns='month', values='stockout_flag').fillna(0)
    
    fig = go.Figure(data=go.Heatmap(
        z=heatmap_pivot.values,
        x=heatmap_pivot.columns.tolist(),
        y=heatmap_pivot.index.tolist(),
        colorscale='RdYlGn_r',
        text=heatmap_pivot.values.astype(int),
        texttemplate="%{text}",
        textfont={"size": 10},
        hovertemplate="Category: %{y}<br>Month: %{x}<br>Stockouts: %{z}<extra></extra>"
    ))
    
    fig.update_layout(
        title={"text": "<b>Stockout Heatmap by Category & Month</b>", "font": {"size": 16}},
        xaxis_title="Month",
        yaxis_title="Category",
        height=280,
        margin=dict(l=120, r=20, t=60, b=60),
        paper_bgcolor='white',
    )
    
    return fig


def create_top_products_table(data):
    """Create top products table."""
    sales = data['sales'].copy()
    products = data['products']
    
    product_revenue = sales.groupby('sku_id')['revenue'].sum().reset_index()
    product_revenue = product_revenue.merge(products[['sku_id', 'product_name', 'category']], on='sku_id')
    top_10 = product_revenue.nlargest(10, 'revenue')
    
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=['<b>Rank</b>', '<b>SKU</b>', '<b>Product Name</b>', '<b>Category</b>', '<b>Revenue</b>'],
            fill_color='#1f77b4',
            font=dict(color='white', size=12),
            align='left',
            height=30
        ),
        cells=dict(
            values=[
                list(range(1, 11)),
                top_10['sku_id'],
                top_10['product_name'].str[:35] + '...',
                top_10['category'],
                top_10['revenue'].apply(lambda x: f'${x:,.0f}')
            ],
            fill_color=[['#f8f9fa', 'white'] * 5],
            align='left',
            height=25,
            font=dict(size=11)
        )
    )])
    
    fig.update_layout(
        title={"text": "<b>Top 10 Products by Revenue</b>", "font": {"size": 16}},
        height=350,
        margin=dict(l=20, r=20, t=60, b=20),
        paper_bgcolor='white',
    )
    
    return fig


def create_full_dashboard():
    """Generate the complete HTML dashboard."""
    print("=" * 60)
    print("ReplenishIQ Dashboard Generator v2")
    print("=" * 60)
    
    print("\nLoading data...")
    data = load_data()
    
    print("Creating visualizations...")
    
    charts = {
        'kpi': create_kpi_section(data),
        'revenue': create_revenue_chart(data),
        'category': create_category_chart(data),
        'instock': create_instock_trend(data),
        'alerts': create_alert_charts(data),
        'clusters': create_cluster_chart(data),
        'supplier': create_supplier_chart(data),
        'heatmap': create_stockout_heatmap(data),
        'top_products': create_top_products_table(data),
    }
    
    # Build HTML
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>ReplenishIQ Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .header {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: white;
            padding: 25px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }
        .header h1 {
            margin: 0;
            font-size: 28px;
            font-weight: 700;
            letter-spacing: -0.5px;
        }
        .header p {
            margin: 5px 0 0 0;
            opacity: 0.8;
            font-size: 14px;
        }
        .header-right {
            text-align: right;
            font-size: 13px;
            opacity: 0.9;
        }
        .container {
            max-width: 1600px;
            margin: 0 auto;
            padding: 25px;
        }
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
        }
        .chart-card {
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            overflow: hidden;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .chart-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }
        .full-width {
            grid-column: span 2;
        }
        .section-header {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            margin: 25px 0 15px 0;
            grid-column: span 2;
            font-size: 16px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .section-header span {
            font-size: 20px;
        }
        @media (max-width: 1200px) {
            .dashboard-grid { grid-template-columns: 1fr; }
            .full-width, .section-header { grid-column: span 1; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>📊 ReplenishIQ Supply Chain Dashboard</h1>
            <p>Inventory Analytics & Exception Management System</p>
        </div>
        <div class="header-right">
            <div>Last Updated: """ + pd.Timestamp.now().strftime('%Y-%m-%d %H:%M') + """</div>
            <div>500 SKUs | 12 Months Data</div>
        </div>
    </div>
    
    <div class="container">
        <div class="dashboard-grid">
            <!-- KPI Section -->
            <div class="chart-card full-width" id="kpi"></div>
            
            <!-- Sales Section -->
            <div class="section-header"><span>💰</span> Sales & Revenue Analysis</div>
            <div class="chart-card" id="revenue"></div>
            <div class="chart-card" id="category"></div>
            
            <!-- Inventory Section -->
            <div class="section-header"><span>📦</span> Inventory Health</div>
            <div class="chart-card" id="instock"></div>
            <div class="chart-card" id="heatmap"></div>
            
            <!-- Alerts Section -->
            <div class="section-header"><span>⚠️</span> Exception Alerts (1,235 Total)</div>
            <div class="chart-card full-width" id="alerts"></div>
            
            <!-- Analytics Section -->
            <div class="section-header"><span>🎯</span> SKU Analytics & Segmentation</div>
            <div class="chart-card" id="clusters"></div>
            <div class="chart-card" id="top_products"></div>
            
            <!-- Supplier Section -->
            <div class="section-header"><span>🚚</span> Supplier Performance</div>
            <div class="chart-card full-width" id="supplier"></div>
        </div>
    </div>
    
    <script>
"""
    
    # Add chart JavaScript
    for chart_id, fig in charts.items():
        chart_json = fig.to_json()
        html_content += f"""
        Plotly.newPlot('{chart_id}', {chart_json}.data, {chart_json}.layout, {{responsive: true, displayModeBar: false}});
"""
    
    html_content += """
    </script>
</body>
</html>"""
    
    # Save
    project_root = get_project_root()
    output_path = os.path.join(project_root, 'dashboard.html')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n✅ Dashboard saved to: {output_path}")
    
    print("\n" + "=" * 60)
    print("Dashboard Generation Complete!")
    print("=" * 60)
    
    return output_path


if __name__ == "__main__":
    create_full_dashboard()
