"""
ReplenishIQ Exception Alert Engine
Automatically detects and flags inventory exceptions that need attention.

Exception Types:
1. Stockout Alert - Inventory at zero
2. Low Stock Alert - Below safety stock
3. Overstock Alert - Above max level
4. SLG Breach Alert - Below service level goal
5. Demand Spike Alert - Unusual demand increase
6. Supplier Delay Alert - Late deliveries
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import warnings
warnings.filterwarnings('ignore')

def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_data():
    """Load all required data files."""
    project_root = get_project_root()
    
    products = pd.read_csv(os.path.join(project_root, 'data', 'processed', 'dim_products.csv'))
    sales = pd.read_csv(os.path.join(project_root, 'data', 'processed', 'fact_sales.csv'))
    inventory = pd.read_csv(os.path.join(project_root, 'data', 'processed', 'fact_inventory.csv'))
    orders = pd.read_csv(os.path.join(project_root, 'data', 'processed', 'fact_replenishment_orders.csv'))
    
    # Convert dates
    sales['date'] = pd.to_datetime(sales['date'])
    inventory['date'] = pd.to_datetime(inventory['date'])
    orders['order_date'] = pd.to_datetime(orders['order_date'])
    orders['expected_delivery_date'] = pd.to_datetime(orders['expected_delivery_date'])
    orders['actual_delivery_date'] = pd.to_datetime(orders['actual_delivery_date'])
    
    return products, sales, inventory, orders


class AlertPriority:
    """Alert priority levels."""
    CRITICAL = 1  # Immediate action required
    HIGH = 2      # Action needed today
    MEDIUM = 3    # Review this week
    LOW = 4       # Monitor


class Alert:
    """Represents a single exception alert."""
    
    def __init__(self, alert_type, sku_id, priority, message, details=None):
        self.alert_type = alert_type
        self.sku_id = sku_id
        self.priority = priority
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now()
    
    def to_dict(self):
        return {
            'alert_type': self.alert_type,
            'sku_id': self.sku_id,
            'priority': self.priority,
            'priority_label': self._priority_label(),
            'message': self.message,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            **self.details
        }
    
    def _priority_label(self):
        labels = {1: 'CRITICAL', 2: 'HIGH', 3: 'MEDIUM', 4: 'LOW'}
        return labels.get(self.priority, 'UNKNOWN')
    
    def __repr__(self):
        return f"Alert({self._priority_label()}: {self.alert_type} - {self.sku_id})"


class ExceptionAlertEngine:
    """
    Main alert engine that detects and generates exception alerts.
    """
    
    def __init__(self):
        self.products, self.sales, self.inventory, self.orders = load_data()
        self.alerts = []
        
        # Thresholds (configurable)
        self.thresholds = {
            'stockout_days_critical': 7,    # 7+ consecutive stockout days
            'stockout_days_high': 3,        # 3+ consecutive stockout days
            'low_stock_pct': 0.5,           # Below 50% of safety stock
            'overstock_pct': 1.5,           # Above 150% of max level
            'slg_breach_pct': 0.05,         # 5% below SLG target
            'demand_spike_std': 2.0,        # 2 standard deviations above mean
            'supplier_delay_days': 3        # 3+ days late
        }
    
    def detect_all_exceptions(self, lookback_days=30):
        """
        Run all exception detection rules.
        
        Args:
            lookback_days: Number of days to analyze
        """
        self.alerts = []
        
        # Get recent data
        cutoff_date = self.inventory['date'].max() - timedelta(days=lookback_days)
        recent_inventory = self.inventory[self.inventory['date'] >= cutoff_date]
        recent_sales = self.sales[self.sales['date'] >= cutoff_date]
        recent_orders = self.orders[self.orders['order_date'] >= cutoff_date]
        
        # Run detection rules
        self._detect_stockouts(recent_inventory)
        self._detect_low_stock(recent_inventory)
        self._detect_overstock(recent_inventory)
        self._detect_slg_breach(recent_inventory)
        self._detect_demand_spikes(recent_sales)
        self._detect_supplier_delays(recent_orders)
        
        return self.alerts


    def _detect_stockouts(self, inventory_df):
        """Detect stockout exceptions."""
        # Find SKUs with stockouts
        stockout_data = inventory_df[inventory_df['stockout_flag'] == True]
        
        for sku_id in stockout_data['sku_id'].unique():
            sku_stockouts = stockout_data[stockout_data['sku_id'] == sku_id]
            stockout_days = len(sku_stockouts)
            
            product = self.products[self.products['sku_id'] == sku_id]
            product_name = product['product_name'].values[0][:50] if len(product) > 0 else 'Unknown'
            
            if stockout_days >= self.thresholds['stockout_days_critical']:
                self.alerts.append(Alert(
                    alert_type='STOCKOUT',
                    sku_id=sku_id,
                    priority=AlertPriority.CRITICAL,
                    message=f'Critical stockout: {stockout_days} days without inventory',
                    details={
                        'product_name': product_name,
                        'stockout_days': stockout_days,
                        'action': 'Expedite order immediately'
                    }
                ))
            elif stockout_days >= self.thresholds['stockout_days_high']:
                self.alerts.append(Alert(
                    alert_type='STOCKOUT',
                    sku_id=sku_id,
                    priority=AlertPriority.HIGH,
                    message=f'Stockout alert: {stockout_days} days without inventory',
                    details={
                        'product_name': product_name,
                        'stockout_days': stockout_days,
                        'action': 'Place urgent order'
                    }
                ))
    
    def _detect_low_stock(self, inventory_df):
        """Detect low stock (below safety stock) exceptions."""
        latest_date = inventory_df['date'].max()
        latest_inventory = inventory_df[inventory_df['date'] == latest_date]
        
        for _, row in latest_inventory.iterrows():
            if row['on_hand_qty'] < row['safety_stock'] * self.thresholds['low_stock_pct']:
                product = self.products[self.products['sku_id'] == row['sku_id']]
                product_name = product['product_name'].values[0][:50] if len(product) > 0 else 'Unknown'
                
                self.alerts.append(Alert(
                    alert_type='LOW_STOCK',
                    sku_id=row['sku_id'],
                    priority=AlertPriority.HIGH,
                    message=f'Inventory critically low: {row["on_hand_qty"]} units (safety stock: {row["safety_stock"]})',
                    details={
                        'product_name': product_name,
                        'current_qty': row['on_hand_qty'],
                        'safety_stock': row['safety_stock'],
                        'action': 'Review reorder status'
                    }
                ))
    
    def _detect_overstock(self, inventory_df):
        """Detect overstock exceptions."""
        latest_date = inventory_df['date'].max()
        latest_inventory = inventory_df[inventory_df['date'] == latest_date]
        
        for _, row in latest_inventory.iterrows():
            product = self.products[self.products['sku_id'] == row['sku_id']]
            if len(product) == 0:
                continue
            
            max_level = product['max_stock_level'].values[0]
            
            if row['on_hand_qty'] > max_level * self.thresholds['overstock_pct']:
                self.alerts.append(Alert(
                    alert_type='OVERSTOCK',
                    sku_id=row['sku_id'],
                    priority=AlertPriority.MEDIUM,
                    message=f'Excess inventory: {row["on_hand_qty"]} units (max: {max_level})',
                    details={
                        'product_name': product['product_name'].values[0][:50],
                        'current_qty': row['on_hand_qty'],
                        'max_level': max_level,
                        'excess_units': row['on_hand_qty'] - max_level,
                        'action': 'Consider promotion or transfer'
                    }
                ))


    def _detect_slg_breach(self, inventory_df):
        """Detect service level goal breaches."""
        # Calculate in-stock rate per SKU
        instock_rates = inventory_df.groupby('sku_id').agg({
            'instock_flag': 'mean'
        }).reset_index()
        instock_rates.columns = ['sku_id', 'instock_rate']
        
        # Merge with SLG targets
        merged = instock_rates.merge(
            self.products[['sku_id', 'product_name', 'slg_target']], 
            on='sku_id'
        )
        
        for _, row in merged.iterrows():
            if row['instock_rate'] < row['slg_target'] - self.thresholds['slg_breach_pct']:
                gap = (row['slg_target'] - row['instock_rate']) * 100
                self.alerts.append(Alert(
                    alert_type='SLG_BREACH',
                    sku_id=row['sku_id'],
                    priority=AlertPriority.HIGH,
                    message=f'Service level below target: {row["instock_rate"]*100:.1f}% vs {row["slg_target"]*100:.1f}% target',
                    details={
                        'product_name': row['product_name'][:50],
                        'actual_slg': round(row['instock_rate'] * 100, 1),
                        'target_slg': round(row['slg_target'] * 100, 1),
                        'gap_pct': round(gap, 1),
                        'action': 'Increase safety stock or reorder point'
                    }
                ))
    
    def _detect_demand_spikes(self, sales_df):
        """Detect unusual demand spikes."""
        # Calculate demand statistics per SKU
        demand_stats = sales_df.groupby('sku_id').agg({
            'units_sold': ['mean', 'std', 'max']
        }).reset_index()
        demand_stats.columns = ['sku_id', 'avg_demand', 'std_demand', 'max_demand']
        
        # Find recent spikes
        recent_date = sales_df['date'].max()
        recent_sales = sales_df[sales_df['date'] == recent_date]
        
        for _, row in recent_sales.iterrows():
            stats = demand_stats[demand_stats['sku_id'] == row['sku_id']]
            if len(stats) == 0:
                continue
            
            avg = stats['avg_demand'].values[0]
            std = stats['std_demand'].values[0]
            
            if std > 0 and row['units_sold'] > avg + (self.thresholds['demand_spike_std'] * std):
                product = self.products[self.products['sku_id'] == row['sku_id']]
                product_name = product['product_name'].values[0][:50] if len(product) > 0 else 'Unknown'
                
                self.alerts.append(Alert(
                    alert_type='DEMAND_SPIKE',
                    sku_id=row['sku_id'],
                    priority=AlertPriority.MEDIUM,
                    message=f'Unusual demand spike: {row["units_sold"]} units (avg: {avg:.1f})',
                    details={
                        'product_name': product_name,
                        'current_demand': row['units_sold'],
                        'avg_demand': round(avg, 1),
                        'std_demand': round(std, 1),
                        'action': 'Monitor inventory and consider expediting orders'
                    }
                ))
    
    def _detect_supplier_delays(self, orders_df):
        """Detect supplier delivery delays."""
        # Find late deliveries
        late_orders = orders_df[
            orders_df['actual_delivery_date'] > orders_df['expected_delivery_date']
        ].copy()
        
        late_orders['days_late'] = (
            late_orders['actual_delivery_date'] - late_orders['expected_delivery_date']
        ).dt.days
        
        for _, row in late_orders.iterrows():
            if row['days_late'] >= self.thresholds['supplier_delay_days']:
                product = self.products[self.products['sku_id'] == row['sku_id']]
                product_name = product['product_name'].values[0][:50] if len(product) > 0 else 'Unknown'
                
                priority = AlertPriority.HIGH if row['days_late'] >= 7 else AlertPriority.MEDIUM
                
                self.alerts.append(Alert(
                    alert_type='SUPPLIER_DELAY',
                    sku_id=row['sku_id'],
                    priority=priority,
                    message=f'Supplier delivery {row["days_late"]} days late',
                    details={
                        'product_name': product_name,
                        'order_id': row['order_id'],
                        'supplier_id': row['supplier_id'],
                        'days_late': row['days_late'],
                        'action': 'Contact supplier and review backup options'
                    }
                ))


    def get_alerts_summary(self):
        """Get summary of all alerts by type and priority."""
        if not self.alerts:
            return "No alerts detected."
        
        df = pd.DataFrame([a.to_dict() for a in self.alerts])
        
        summary = {
            'total_alerts': len(self.alerts),
            'by_priority': df.groupby('priority_label').size().to_dict(),
            'by_type': df.groupby('alert_type').size().to_dict(),
            'critical_count': len([a for a in self.alerts if a.priority == AlertPriority.CRITICAL]),
            'high_count': len([a for a in self.alerts if a.priority == AlertPriority.HIGH])
        }
        
        return summary
    
    def export_alerts(self, filename='alerts.csv'):
        """Export alerts to CSV."""
        if not self.alerts:
            print("No alerts to export.")
            return None
        
        df = pd.DataFrame([a.to_dict() for a in self.alerts])
        
        project_root = get_project_root()
        output_path = os.path.join(project_root, 'data', 'processed', filename)
        df.to_csv(output_path, index=False)
        
        return output_path


def run_alert_detection():
    """Run full alert detection and display results."""
    print("=" * 60)
    print("ReplenishIQ Exception Alert Engine")
    print("=" * 60)
    
    engine = ExceptionAlertEngine()
    
    print("\nDetecting exceptions (last 30 days)...")
    alerts = engine.detect_all_exceptions(lookback_days=30)
    
    print(f"\nTotal Alerts Detected: {len(alerts)}")
    
    # Summary
    summary = engine.get_alerts_summary()
    
    print("\n" + "-" * 40)
    print("Alerts by Priority:")
    print("-" * 40)
    for priority, count in sorted(summary.get('by_priority', {}).items()):
        print(f"  {priority}: {count}")
    
    print("\n" + "-" * 40)
    print("Alerts by Type:")
    print("-" * 40)
    for alert_type, count in summary.get('by_type', {}).items():
        print(f"  {alert_type}: {count}")
    
    # Show top critical/high alerts
    critical_high = [a for a in alerts if a.priority <= AlertPriority.HIGH]
    
    if critical_high:
        print("\n" + "-" * 40)
        print(f"Top {min(10, len(critical_high))} Critical/High Priority Alerts:")
        print("-" * 40)
        for alert in sorted(critical_high, key=lambda x: x.priority)[:10]:
            print(f"\n  [{alert._priority_label()}] {alert.alert_type}")
            print(f"  SKU: {alert.sku_id}")
            print(f"  Message: {alert.message}")
            if 'action' in alert.details:
                print(f"  Action: {alert.details['action']}")
    
    # Export
    output_path = engine.export_alerts()
    if output_path:
        print(f"\nAlerts exported to: {output_path}")
    
    print("\n" + "=" * 60)
    print("Alert Detection Complete!")
    print("=" * 60)
    
    return engine


if __name__ == "__main__":
    run_alert_detection()
