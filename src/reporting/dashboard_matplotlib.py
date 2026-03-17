"""
ReplenishIQ Dashboard - Matplotlib/Seaborn Version
Generates professional static charts as PNG images and combines into HTML dashboard.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.gridspec import GridSpec
import os
import base64
from io import BytesIO

# Set style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("Set2")

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


def fig_to_base64(fig):
    """Convert matplotlib figure to base64 string."""
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='white', edgecolor='none')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return img_str


def create_kpi_cards(data):
    """Create KPI summary cards."""
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
    
    fig, axes = plt.subplots(1, 6, figsize=(18, 3))
    fig.patch.set_facecolor('white')
    
    kpis = [
        ('Total Revenue', f'${total_revenue/1e6:.1f}M', '#1f77b4'),
        ('Units Sold', f'{total_units/1e6:.2f}M', '#2ca02c'),
        ('In-Stock Rate', f'{instock_rate:.1f}%', '#2ca02c' if instock_rate >= 90 else '#ff7f0e'),
        ('Stockout Rate', f'{stockout_rate:.1f}%', '#d62728' if stockout_rate > 15 else '#ff7f0e'),
        ('Active SKUs', f'{sku_count}', '#9467bd'),
        ('Critical Alerts', f'{critical_alerts}', '#d62728'),
    ]
    
    for ax, (title, value, color) in zip(axes, kpis):
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.text(0.5, 0.65, value, ha='center', va='center', fontsize=28, fontweight='bold', color=color)
        ax.text(0.5, 0.25, title, ha='center', va='center', fontsize=12, color='#333')
        ax.axis('off')
        ax.set_facecolor('#f8f9fa')
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_color('#ddd')
    
    plt.tight_layout()
    return fig_to_base64(fig)


def create_revenue_chart(data):
    """Create monthly revenue trend."""
    sales = data['sales'].copy()
    sales['month'] = sales['date'].dt.to_period('M').astype(str)
    
    monthly = sales.groupby('month').agg({
        'revenue': 'sum',
        'units_sold': 'sum'
    }).reset_index()
    
    fig, ax1 = plt.subplots(figsize=(10, 5))
    
    # Bar chart for revenue
    bars = ax1.bar(monthly['month'], monthly['revenue']/1e6, color='#1f77b4', alpha=0.8, label='Revenue')
    ax1.set_xlabel('Month', fontsize=11)
    ax1.set_ylabel('Revenue ($ Millions)', color='#1f77b4', fontsize=11)
    ax1.tick_params(axis='y', labelcolor='#1f77b4')
    ax1.tick_params(axis='x', rotation=45)
    
    # Line chart for units
    ax2 = ax1.twinx()
    ax2.plot(monthly['month'], monthly['units_sold']/1e3, color='#ff7f0e', linewidth=3, marker='o', markersize=8, label='Units Sold')
    ax2.set_ylabel('Units Sold (Thousands)', color='#ff7f0e', fontsize=11)
    ax2.tick_params(axis='y', labelcolor='#ff7f0e')
    
    plt.title('Monthly Revenue & Sales Volume', fontsize=14, fontweight='bold', pad=15)
    
    # Legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
    
    plt.tight_layout()
    return fig_to_base64(fig)


def create_category_chart(data):
    """Create category performance chart."""
    sales = data['sales'].copy()
    products = data['products']
    
    sales_cat = sales.merge(products[['sku_id', 'category']], on='sku_id', how='left')
    
    # Handle column naming after merge
    cat_col = 'category'
    if 'category' not in sales_cat.columns:
        if 'category_y' in sales_cat.columns:
            cat_col = 'category_y'
        elif 'category_x' in sales_cat.columns:
            cat_col = 'category_x'
    
    category_totals = sales_cat.groupby(cat_col)['revenue'].sum().sort_values()
    
    fig, ax = plt.subplots(figsize=(10, 5))
    
    colors = sns.color_palette("Set2", len(category_totals))
    bars = ax.barh(category_totals.index, category_totals.values/1e6, color=colors)
    
    # Add value labels
    for bar, val in zip(bars, category_totals.values):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2, 
                f'${val/1e6:.1f}M', va='center', fontsize=10)
    
    ax.set_xlabel('Revenue ($ Millions)', fontsize=11)
    ax.set_title('Revenue by Category', fontsize=14, fontweight='bold', pad=15)
    ax.set_xlim(0, category_totals.max()/1e6 * 1.15)
    
    plt.tight_layout()
    return fig_to_base64(fig)


def create_instock_trend(data):
    """Create in-stock rate trend by category."""
    inventory = data['inventory'].copy()
    products = data['products']
    
    inv_cat = inventory.merge(products[['sku_id', 'category']], on='sku_id', how='left')
    
    # Handle column naming
    cat_col = 'category'
    if 'category' not in inv_cat.columns:
        if 'category_y' in inv_cat.columns:
            cat_col = 'category_y'
        elif 'category_x' in inv_cat.columns:
            cat_col = 'category_x'
    inv_cat['category'] = inv_cat[cat_col]
    
    inv_cat['month'] = inv_cat['date'].dt.to_period('M').astype(str)
    
    monthly_instock = inv_cat.groupby(['month', 'category'])['instock_flag'].mean().reset_index()
    monthly_instock['instock_pct'] = monthly_instock['instock_flag'] * 100
    
    fig, ax = plt.subplots(figsize=(10, 5))
    
    categories = monthly_instock['category'].unique()
    colors = sns.color_palette("Set2", len(categories))
    
    for cat, color in zip(categories, colors):
        cat_data = monthly_instock[monthly_instock['category'] == cat]
        ax.plot(cat_data['month'], cat_data['instock_pct'], marker='o', linewidth=2, 
                label=cat, color=color, markersize=6)
    
    # Add 95% target line
    ax.axhline(y=95, color='red', linestyle='--', linewidth=2, label='95% Target')
    
    ax.set_xlabel('Month', fontsize=11)
    ax.set_ylabel('In-Stock Rate (%)', fontsize=11)
    ax.set_title('In-Stock Rate Trend by Category', fontsize=14, fontweight='bold', pad=15)
    ax.set_ylim(75, 102)
    ax.legend(loc='lower left', fontsize=9)
    ax.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    return fig_to_base64(fig)


def create_stockout_heatmap(data):
    """Create stockout heatmap."""
    inventory = data['inventory'].copy()
    products = data['products']
    
    inv_cat = inventory.merge(products[['sku_id', 'category']], on='sku_id', how='left')
    
    # Handle column naming
    cat_col = 'category'
    if 'category' not in inv_cat.columns:
        if 'category_y' in inv_cat.columns:
            cat_col = 'category_y'
        elif 'category_x' in inv_cat.columns:
            cat_col = 'category_x'
    inv_cat['category'] = inv_cat[cat_col]
    
    inv_cat['month'] = inv_cat['date'].dt.strftime('%Y-%m')
    
    heatmap_data = inv_cat.groupby(['category', 'month'])['stockout_flag'].sum().reset_index()
    heatmap_pivot = heatmap_data.pivot(index='category', columns='month', values='stockout_flag').fillna(0)
    
    fig, ax = plt.subplots(figsize=(12, 4))
    
    sns.heatmap(heatmap_pivot, annot=True, fmt='.0f', cmap='RdYlGn_r', 
                linewidths=0.5, ax=ax, cbar_kws={'label': 'Stockout Count'})
    
    ax.set_title('Stockout Heatmap by Category & Month', fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel('Month', fontsize=11)
    ax.set_ylabel('Category', fontsize=11)
    plt.xticks(rotation=45, ha='right')
    
    plt.tight_layout()
    return fig_to_base64(fig)


def create_alert_charts(data):
    """Create alert summary charts."""
    alerts = data['alerts'].copy()
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Pie chart - Priority
    priority_counts = alerts['priority_label'].value_counts()
    colors_priority = {'CRITICAL': '#d62728', 'HIGH': '#ff7f0e', 'MEDIUM': '#ffd700', 'LOW': '#2ca02c'}
    pie_colors = [colors_priority.get(p, '#999') for p in priority_counts.index]
    
    wedges, texts, autotexts = ax1.pie(priority_counts.values, labels=priority_counts.index, 
                                        autopct='%1.0f%%', colors=pie_colors, startangle=90,
                                        explode=[0.02]*len(priority_counts))
    ax1.set_title('Alerts by Priority', fontsize=14, fontweight='bold', pad=15)
    
    # Add count labels
    for i, (wedge, count) in enumerate(zip(wedges, priority_counts.values)):
        angle = (wedge.theta2 - wedge.theta1)/2 + wedge.theta1
        x = 0.7 * np.cos(np.radians(angle))
        y = 0.7 * np.sin(np.radians(angle))
    
    # Bar chart - Type
    type_counts = alerts['alert_type'].value_counts()
    bars = ax2.barh(type_counts.index, type_counts.values, color='#1f77b4')
    
    # Add value labels
    for bar, val in zip(bars, type_counts.values):
        ax2.text(bar.get_width() + 5, bar.get_y() + bar.get_height()/2, 
                str(val), va='center', fontsize=10)
    
    ax2.set_xlabel('Count', fontsize=11)
    ax2.set_title('Alerts by Type', fontsize=14, fontweight='bold', pad=15)
    ax2.set_xlim(0, type_counts.max() * 1.15)
    
    plt.tight_layout()
    return fig_to_base64(fig)


def create_cluster_chart(data):
    """Create SKU cluster scatter plot."""
    clusters = data['clusters'].copy()
    
    clusters['avg_daily_demand'] = pd.to_numeric(clusters['avg_daily_demand'], errors='coerce').fillna(0)
    clusters['total_revenue'] = pd.to_numeric(clusters['total_revenue'], errors='coerce').fillna(0)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    color_map = {'A': '#2ca02c', 'B': '#1f77b4', 'C': '#ff7f0e', 'D': '#d62728'}
    
    for label in ['A', 'B', 'C', 'D']:
        cluster_data = clusters[clusters['cluster_label'] == label]
        ax.scatter(cluster_data['avg_daily_demand'], cluster_data['total_revenue']/1e6,
                   c=color_map[label], label=f'Cluster {label}', alpha=0.6, s=50, edgecolors='white')
    
    ax.set_xlabel('Average Daily Demand (units)', fontsize=11)
    ax.set_ylabel('Total Revenue ($ Millions)', fontsize=11)
    ax.set_title('SKU Segmentation (A/B/C/D Clusters)', fontsize=14, fontweight='bold', pad=15)
    ax.legend(title='Cluster', loc='upper right')
    
    plt.tight_layout()
    return fig_to_base64(fig)


def create_supplier_chart(data):
    """Create supplier performance chart."""
    suppliers = data['suppliers'].copy()
    
    fig, ax = plt.subplots(figsize=(10, 5))
    
    x = np.arange(len(suppliers))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, suppliers['fill_rate'] * 100, width, label='Fill Rate (%)', color='#1f77b4')
    bars2 = ax.bar(x + width/2, suppliers['on_time_delivery_rate'] * 100, width, label='On-Time Rate (%)', color='#2ca02c')
    
    ax.set_xlabel('Supplier', fontsize=11)
    ax.set_ylabel('Rate (%)', fontsize=11)
    ax.set_title('Supplier Performance Comparison', fontsize=14, fontweight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(suppliers['supplier_name'], rotation=45, ha='right')
    ax.legend()
    ax.set_ylim(0, 110)
    
    # Add value labels
    for bar in bars1:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                f'{bar.get_height():.0f}', ha='center', va='bottom', fontsize=9)
    for bar in bars2:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                f'{bar.get_height():.0f}', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    return fig_to_base64(fig)


def create_top_products_chart(data):
    """Create top products bar chart."""
    sales = data['sales'].copy()
    products = data['products']
    
    product_revenue = sales.groupby('sku_id')['revenue'].sum().reset_index()
    product_revenue = product_revenue.merge(products[['sku_id', 'product_name', 'category']], on='sku_id')
    top_10 = product_revenue.nlargest(10, 'revenue')
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    colors = sns.color_palette("Set2", 10)
    bars = ax.barh(range(10), top_10['revenue'].values/1e6, color=colors)
    
    ax.set_yticks(range(10))
    ax.set_yticklabels([f"{row['sku_id'][:10]}..." for _, row in top_10.iterrows()], fontsize=10)
    ax.invert_yaxis()
    
    # Add value labels
    for bar, val in zip(bars, top_10['revenue'].values):
        ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2, 
                f'${val/1e6:.2f}M', va='center', fontsize=10)
    
    ax.set_xlabel('Revenue ($ Millions)', fontsize=11)
    ax.set_title('Top 10 Products by Revenue', fontsize=14, fontweight='bold', pad=15)
    ax.set_xlim(0, top_10['revenue'].max()/1e6 * 1.2)
    
    plt.tight_layout()
    return fig_to_base64(fig)


def create_full_dashboard():
    """Generate complete HTML dashboard with matplotlib charts."""
    print("=" * 60)
    print("ReplenishIQ Dashboard - Matplotlib/Seaborn Version")
    print("=" * 60)
    
    print("\nLoading data...")
    data = load_data()
    
    print("Creating visualizations...")
    
    charts = {}
    
    print("  - KPI Cards...")
    charts['kpi'] = create_kpi_cards(data)
    
    print("  - Revenue Chart...")
    charts['revenue'] = create_revenue_chart(data)
    
    print("  - Category Chart...")
    charts['category'] = create_category_chart(data)
    
    print("  - In-Stock Trend...")
    charts['instock'] = create_instock_trend(data)
    
    print("  - Stockout Heatmap...")
    charts['heatmap'] = create_stockout_heatmap(data)
    
    print("  - Alert Charts...")
    charts['alerts'] = create_alert_charts(data)
    
    print("  - Cluster Chart...")
    charts['clusters'] = create_cluster_chart(data)
    
    print("  - Supplier Chart...")
    charts['supplier'] = create_supplier_chart(data)
    
    print("  - Top Products...")
    charts['top_products'] = create_top_products_chart(data)
    
    # Build HTML
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>ReplenishIQ Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .header {{
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: white;
            padding: 25px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 700;
        }}
        .header p {{
            margin: 5px 0 0 0;
            opacity: 0.8;
            font-size: 14px;
        }}
        .header-right {{
            text-align: right;
            font-size: 13px;
            opacity: 0.9;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 25px;
        }}
        .dashboard-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
        }}
        .chart-card {{
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            overflow: hidden;
            padding: 15px;
        }}
        .chart-card img {{
            width: 100%;
            height: auto;
            display: block;
        }}
        .full-width {{
            grid-column: span 2;
        }}
        .section-header {{
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            margin: 25px 0 15px 0;
            grid-column: span 2;
            font-size: 16px;
            font-weight: 600;
        }}
        @media (max-width: 1000px) {{
            .dashboard-grid {{ grid-template-columns: 1fr; }}
            .full-width, .section-header {{ grid-column: span 1; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>📊 ReplenishIQ Supply Chain Dashboard</h1>
            <p>Inventory Analytics & Exception Management System</p>
        </div>
        <div class="header-right">
            <div>Last Updated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}</div>
            <div>500 SKUs | 12 Months Data</div>
        </div>
    </div>
    
    <div class="container">
        <div class="dashboard-grid">
            <!-- KPI Section -->
            <div class="chart-card full-width">
                <img src="data:image/png;base64,{charts['kpi']}" alt="KPI Cards">
            </div>
            
            <!-- Sales Section -->
            <div class="section-header">💰 Sales & Revenue Analysis</div>
            <div class="chart-card">
                <img src="data:image/png;base64,{charts['revenue']}" alt="Revenue Trend">
            </div>
            <div class="chart-card">
                <img src="data:image/png;base64,{charts['category']}" alt="Category Performance">
            </div>
            
            <!-- Inventory Section -->
            <div class="section-header">📦 Inventory Health</div>
            <div class="chart-card">
                <img src="data:image/png;base64,{charts['instock']}" alt="In-Stock Trend">
            </div>
            <div class="chart-card">
                <img src="data:image/png;base64,{charts['heatmap']}" alt="Stockout Heatmap">
            </div>
            
            <!-- Alerts Section -->
            <div class="section-header">⚠️ Exception Alerts (1,235 Total)</div>
            <div class="chart-card full-width">
                <img src="data:image/png;base64,{charts['alerts']}" alt="Alert Summary">
            </div>
            
            <!-- Analytics Section -->
            <div class="section-header">🎯 SKU Analytics & Segmentation</div>
            <div class="chart-card">
                <img src="data:image/png;base64,{charts['clusters']}" alt="SKU Clusters">
            </div>
            <div class="chart-card">
                <img src="data:image/png;base64,{charts['top_products']}" alt="Top Products">
            </div>
            
            <!-- Supplier Section -->
            <div class="section-header">🚚 Supplier Performance</div>
            <div class="chart-card full-width">
                <img src="data:image/png;base64,{charts['supplier']}" alt="Supplier Scorecard">
            </div>
        </div>
    </div>
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
