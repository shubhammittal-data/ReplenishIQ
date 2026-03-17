"""
ReplenishIQ Interactive Dashboard
Creates professional visualizations using Plotly.
Generates an HTML dashboard that can be opened in any browser.
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
    """Load all dashboard data."""
    project_root = get_project_root()
    tableau_dir = os.path.join(project_root, 'tableau')
    data_dir = os.path.join(project_root, 'data', 'processed')
    
    data = {}
    
    # Load from tableau folder
    data['kpi'] = pd.read_csv(os.path.join(tableau_dir, 'kpi_summary.csv'))
    data['inventory_health'] = pd.read_csv(os.path.join(tableau_dir, 'daily_inventory_health.csv'))
    data['sales_category'] = pd.read_csv(os.path.join(tableau_dir, 'daily_sales_by_category.csv'))
    data['monthly_sales'] = pd.read_csv(os.path.join(tableau_dir, 'monthly_sales_trend.csv'))
    data['supplier'] = pd.read_csv(os.path.join(tableau_dir, 'supplier_scorecard.csv'))
    data['alerts'] = pd.read_csv(os.path.join(tableau_dir, 'exception_dashboard.csv'))
    data['clusters'] = pd.read_csv(os.path.join(tableau_dir, 'sku_clusters.csv'))
    data['top_products'] = pd.read_csv(os.path.join(tableau_dir, 'top_50_products.csv'))
    
    # Load forecasts if available
    try:
        data['forecasts'] = pd.read_csv(os.path.join(tableau_dir, 'forecast_data.csv'))
    except:
        data['forecasts'] = None
    
    # Convert dates
    data['inventory_health']['date'] = pd.to_datetime(data['inventory_health']['date'])
    data['sales_category']['date'] = pd.to_datetime(data['sales_category']['date'])
    
    return data


# =============================================================================
# CHART 1: KPI CARDS
# =============================================================================

def create_kpi_cards(data):
    """Create KPI indicator cards."""
    kpi = data['kpi']
    
    # Get specific KPIs
    total_revenue = kpi[kpi['metric'] == 'Total Revenue']['value'].values[0]
    instock_rate = kpi[kpi['metric'] == 'In-Stock Rate']['value'].values[0]
    stockout_rate = kpi[kpi['metric'] == 'Stockout Rate']['value'].values[0]
    sku_count = kpi[kpi['metric'] == 'SKU Count']['value'].values[0]
    
    fig = go.Figure()
    
    # Create 4 indicator cards
    fig.add_trace(go.Indicator(
        mode="number",
        value=total_revenue,
        title={"text": "Total Revenue", "font": {"size": 16}},
        number={"prefix": "$", "font": {"size": 40}, "valueformat": ",.0f"},
        domain={'x': [0, 0.25], 'y': [0, 1]}
    ))
    
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=instock_rate,
        title={"text": "In-Stock Rate", "font": {"size": 16}},
        number={"suffix": "%", "font": {"size": 30}},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "green" if instock_rate >= 95 else "orange" if instock_rate >= 85 else "red"},
            'threshold': {'line': {'color': "black", 'width': 2}, 'thickness': 0.75, 'value': 95}
        },
        domain={'x': [0.25, 0.5], 'y': [0, 1]}
    ))
    
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=stockout_rate,
        title={"text": "Stockout Rate", "font": {"size": 16}},
        number={"suffix": "%", "font": {"size": 30}},
        gauge={
            'axis': {'range': [0, 50]},
            'bar': {'color': "red" if stockout_rate > 10 else "orange" if stockout_rate > 5 else "green"},
        },
        domain={'x': [0.5, 0.75], 'y': [0, 1]}
    ))
    
    fig.add_trace(go.Indicator(
        mode="number",
        value=sku_count,
        title={"text": "Active SKUs", "font": {"size": 16}},
        number={"font": {"size": 40}},
        domain={'x': [0.75, 1], 'y': [0, 1]}
    ))
    
    fig.update_layout(
        title="Executive KPI Dashboard",
        height=250,
        margin=dict(l=20, r=20, t=60, b=20)
    )
    
    return fig


# =============================================================================
# CHART 2: REVENUE TREND
# =============================================================================

def create_revenue_trend(data):
    """Create monthly revenue trend chart."""
    monthly = data['monthly_sales'].copy()
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(
        go.Bar(
            x=monthly['date'],
            y=monthly['revenue'],
            name="Revenue",
            marker_color='#1f77b4'
        ),
        secondary_y=False
    )
    
    fig.add_trace(
        go.Scatter(
            x=monthly['date'],
            y=monthly['units_sold'],
            name="Units Sold",
            line=dict(color='#ff7f0e', width=3),
            mode='lines+markers'
        ),
        secondary_y=True
    )
    
    fig.update_layout(
        title="Monthly Revenue & Units Sold",
        xaxis_title="Month",
        height=350,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=60, b=20)
    )
    
    fig.update_yaxes(title_text="Revenue ($)", secondary_y=False)
    fig.update_yaxes(title_text="Units Sold", secondary_y=True)
    
    return fig


# =============================================================================
# CHART 3: INVENTORY HEALTH TREND
# =============================================================================

def create_inventory_health_trend(data):
    """Create in-stock rate trend by category."""
    inv = data['inventory_health'].copy()
    
    # Aggregate by date and category - instock_rate is already 0-1 scale
    daily_trend = inv.groupby(['date', 'category']).agg({
        'instock_rate': 'mean'
    }).reset_index()
    
    # Convert to percentage (0-100)
    daily_trend['instock_rate_pct'] = daily_trend['instock_rate'] * 100
    
    fig = px.line(
        daily_trend,
        x='date',
        y='instock_rate_pct',
        color='category',
        title='In-Stock Rate Trend by Category'
    )
    
    # Add target line at 95%
    fig.add_hline(y=95, line_dash="dash", line_color="red", 
                  annotation_text="95% Target", annotation_position="right")
    
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="In-Stock Rate (%)",
        yaxis_range=[80, 102],
        height=350,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=60, r=20, t=60, b=40)
    )
    
    return fig


# =============================================================================
# CHART 4: CATEGORY PERFORMANCE
# =============================================================================

def create_category_performance(data):
    """Create category revenue breakdown."""
    sales = data['sales_category'].copy()
    
    # Aggregate by category
    category_totals = sales.groupby('category').agg({
        'revenue': 'sum',
        'units_sold': 'sum'
    }).reset_index().sort_values('revenue', ascending=True)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=category_totals['category'],
        x=category_totals['revenue'],
        orientation='h',
        marker_color=px.colors.qualitative.Set2[:len(category_totals)],
        text=category_totals['revenue'].apply(lambda x: f'${x/1e6:.1f}M'),
        textposition='outside'
    ))
    
    fig.update_layout(
        title="Revenue by Category",
        xaxis_title="Total Revenue ($)",
        yaxis_title="",
        height=350,
        margin=dict(l=20, r=80, t=60, b=20)
    )
    
    return fig


# =============================================================================
# CHART 5: ALERT SUMMARY
# =============================================================================

def create_alert_summary(data):
    """Create alert priority and type breakdown."""
    alerts = data['alerts'].copy()
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Alerts by Priority", "Alerts by Type"),
        specs=[[{"type": "pie"}, {"type": "bar"}]]
    )
    
    # Priority pie chart
    priority_counts = alerts['priority_label'].value_counts()
    colors = {'CRITICAL': '#d62728', 'HIGH': '#ff7f0e', 'MEDIUM': '#ffbb78', 'LOW': '#2ca02c'}
    
    fig.add_trace(
        go.Pie(
            labels=priority_counts.index,
            values=priority_counts.values,
            marker_colors=[colors.get(p, '#999') for p in priority_counts.index],
            hole=0.4
        ),
        row=1, col=1
    )
    
    # Type bar chart
    type_counts = alerts['alert_type'].value_counts()
    
    fig.add_trace(
        go.Bar(
            x=type_counts.values,
            y=type_counts.index,
            orientation='h',
            marker_color='#1f77b4'
        ),
        row=1, col=2
    )
    
    fig.update_layout(
        title=f"Exception Alerts Summary (Total: {len(alerts)})",
        height=350,
        showlegend=False,
        margin=dict(l=20, r=20, t=80, b=20)
    )
    
    return fig


# =============================================================================
# CHART 6: SKU CLUSTERS
# =============================================================================

def create_cluster_scatter(data):
    """Create SKU cluster visualization."""
    clusters = data['clusters'].copy()
    
    # Ensure numeric columns and handle any issues
    clusters['avg_daily_demand'] = pd.to_numeric(clusters['avg_daily_demand'], errors='coerce').fillna(0)
    clusters['total_revenue'] = pd.to_numeric(clusters['total_revenue'], errors='coerce').fillna(0)
    clusters['inventory_turns'] = pd.to_numeric(clusters['inventory_turns'], errors='coerce').fillna(1)
    
    # Cap inventory_turns for better visualization (some values might be too large)
    clusters['size_value'] = clusters['inventory_turns'].clip(upper=100)
    
    fig = px.scatter(
        clusters,
        x='avg_daily_demand',
        y='total_revenue',
        color='cluster_label',
        size='size_value',
        size_max=20,
        hover_data=['sku_id', 'category', 'inventory_turns'],
        title='SKU Segmentation (A/B/C/D Clusters)',
        color_discrete_map={'A': '#2ca02c', 'B': '#1f77b4', 'C': '#ff7f0e', 'D': '#d62728'}
    )
    
    fig.update_layout(
        xaxis_title="Average Daily Demand (units)",
        yaxis_title="Total Revenue ($)",
        height=400,
        legend_title="Cluster",
        margin=dict(l=60, r=20, t=60, b=40)
    )
    
    fig.update_traces(marker=dict(opacity=0.7, line=dict(width=1, color='white')))
    
    return fig


# =============================================================================
# CHART 7: SUPPLIER SCORECARD
# =============================================================================

def create_supplier_scorecard(data):
    """Create supplier performance comparison."""
    supplier = data['supplier'].copy()
    
    fig = go.Figure()
    
    # Add bars for each metric
    metrics = ['avg_fill_rate', 'on_time_rate', 'reliability_score']
    colors = ['#1f77b4', '#2ca02c', '#ff7f0e']
    
    for i, metric in enumerate(metrics):
        if metric in supplier.columns:
            values = supplier[metric] * 100 if supplier[metric].max() <= 1 else supplier[metric]
            fig.add_trace(go.Bar(
                name=metric.replace('_', ' ').title(),
                x=supplier['supplier_name'],
                y=values,
                marker_color=colors[i]
            ))
    
    fig.update_layout(
        title="Supplier Performance Scorecard",
        xaxis_title="Supplier",
        yaxis_title="Score / Rate (%)",
        barmode='group',
        height=350,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=80, b=20)
    )
    
    return fig


# =============================================================================
# CHART 8: TOP PRODUCTS
# =============================================================================

def create_top_products(data):
    """Create top products table."""
    top = data['top_products'].head(10).copy()
    
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=['<b>SKU</b>', '<b>Product Name</b>', '<b>Category</b>', '<b>Revenue</b>'],
            fill_color='#1f77b4',
            font=dict(color='white', size=12),
            align='left'
        ),
        cells=dict(
            values=[
                top['sku_id'],
                top['product_name'].str[:40] + '...',
                top['category'],
                top['revenue'].apply(lambda x: f'${x:,.0f}')
            ],
            fill_color=[['#f9f9f9', 'white'] * 5],
            align='left',
            height=25
        )
    )])
    
    fig.update_layout(
        title="Top 10 Products by Revenue",
        height=350,
        margin=dict(l=20, r=20, t=60, b=20)
    )
    
    return fig


# =============================================================================
# CHART 9: STOCKOUT HEATMAP
# =============================================================================

def create_stockout_heatmap(data):
    """Create stockout heatmap by category and month."""
    inv = data['inventory_health'].copy()
    inv['month'] = inv['date'].dt.strftime('%Y-%m')
    
    # Aggregate stockouts by month and category
    heatmap_data = inv.groupby(['month', 'category'])['stockout_skus'].sum().reset_index()
    heatmap_pivot = heatmap_data.pivot(index='category', columns='month', values='stockout_skus').fillna(0)
    
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
        title="Stockout Heatmap by Category and Month",
        xaxis_title="Month",
        yaxis_title="Category",
        height=300,
        margin=dict(l=100, r=20, t=60, b=40)
    )
    
    return fig


# =============================================================================
# MAIN DASHBOARD GENERATOR
# =============================================================================

def create_full_dashboard():
    """Generate complete HTML dashboard."""
    print("=" * 60)
    print("ReplenishIQ Dashboard Generator")
    print("=" * 60)
    
    print("\nLoading data...")
    data = load_data()
    
    print("Creating visualizations...")
    
    # Create all charts
    charts = {
        'kpi': create_kpi_cards(data),
        'revenue': create_revenue_trend(data),
        'inventory': create_inventory_health_trend(data),
        'category': create_category_performance(data),
        'alerts': create_alert_summary(data),
        'clusters': create_cluster_scatter(data),
        'supplier': create_supplier_scorecard(data),
        'top_products': create_top_products(data),
        'heatmap': create_stockout_heatmap(data)
    }
    
    # Create combined HTML dashboard
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ReplenishIQ Dashboard</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .header {
                background: linear-gradient(135deg, #1f77b4, #2ca02c);
                color: white;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
                text-align: center;
            }
            .header h1 {
                margin: 0;
                font-size: 28px;
            }
            .header p {
                margin: 5px 0 0 0;
                opacity: 0.9;
            }
            .dashboard-grid {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 20px;
            }
            .chart-container {
                background: white;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                padding: 15px;
            }
            .full-width {
                grid-column: span 2;
            }
            .section-title {
                background: #333;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                margin: 30px 0 20px 0;
                grid-column: span 2;
            }
            @media (max-width: 1200px) {
                .dashboard-grid {
                    grid-template-columns: 1fr;
                }
                .full-width {
                    grid-column: span 1;
                }
                .section-title {
                    grid-column: span 1;
                }
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🏪 ReplenishIQ Supply Chain Dashboard</h1>
            <p>Inventory Analytics & Exception Management System</p>
        </div>
        
        <div class="dashboard-grid">
            <div class="chart-container full-width" id="kpi"></div>
            
            <h2 class="section-title">📊 Sales & Revenue Analysis</h2>
            <div class="chart-container" id="revenue"></div>
            <div class="chart-container" id="category"></div>
            
            <h2 class="section-title">📦 Inventory Health</h2>
            <div class="chart-container" id="inventory"></div>
            <div class="chart-container" id="heatmap"></div>
            
            <h2 class="section-title">⚠️ Exception Alerts</h2>
            <div class="chart-container full-width" id="alerts"></div>
            
            <h2 class="section-title">🎯 SKU Analytics</h2>
            <div class="chart-container" id="clusters"></div>
            <div class="chart-container" id="top_products"></div>
            
            <h2 class="section-title">🚚 Supplier Performance</h2>
            <div class="chart-container full-width" id="supplier"></div>
        </div>
        
        <script>
    """
    
    # Add each chart's JavaScript
    for chart_id, fig in charts.items():
        chart_json = fig.to_json()
        html_content += f"""
            Plotly.newPlot('{chart_id}', {chart_json}.data, {chart_json}.layout, {{responsive: true}});
        """
    
    html_content += """
        </script>
    </body>
    </html>
    """
    
    # Save dashboard
    project_root = get_project_root()
    output_path = os.path.join(project_root, 'dashboard.html')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n✅ Dashboard saved to: {output_path}")
    print("\nOpen this file in your browser to view the interactive dashboard!")
    
    # Also save individual charts
    charts_dir = os.path.join(project_root, 'charts')
    os.makedirs(charts_dir, exist_ok=True)
    
    for chart_id, fig in charts.items():
        fig.write_html(os.path.join(charts_dir, f'{chart_id}.html'))
    
    print(f"Individual charts saved to: {charts_dir}")
    
    print("\n" + "=" * 60)
    print("Dashboard Generation Complete!")
    print("=" * 60)
    
    return charts


if __name__ == "__main__":
    create_full_dashboard()
