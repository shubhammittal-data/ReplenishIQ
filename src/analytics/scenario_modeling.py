"""
ReplenishIQ Scenario Modeling Engine
Simulates "what-if" scenarios to optimize replenishment parameters.

Scenarios supported:
1. Safety Stock Changes - Impact on stockouts and carrying costs
2. Lead Time Changes - Impact on service levels
3. Reorder Point Optimization - Find optimal ROP
4. Service Level Targeting - Calculate parameters for target SLG
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
    """Load required data files."""
    project_root = get_project_root()
    
    products = pd.read_csv(os.path.join(project_root, 'data', 'processed', 'dim_products.csv'))
    sales = pd.read_csv(os.path.join(project_root, 'data', 'processed', 'fact_sales.csv'))
    inventory = pd.read_csv(os.path.join(project_root, 'data', 'processed', 'fact_inventory.csv'))
    
    return products, sales, inventory


class ScenarioSimulator:
    """
    Simulates inventory scenarios to evaluate parameter changes.
    """
    
    def __init__(self):
        self.products, self.sales, self.inventory = load_data()
        self._prepare_demand_stats()
    
    def _prepare_demand_stats(self):
        """Calculate demand statistics for each SKU."""
        demand_stats = self.sales.groupby('sku_id').agg({
            'units_sold': ['mean', 'std', 'sum']
        }).reset_index()
        demand_stats.columns = ['sku_id', 'avg_demand', 'std_demand', 'total_demand']
        demand_stats['std_demand'] = demand_stats['std_demand'].fillna(0)
        
        self.demand_stats = demand_stats
        
    def simulate_inventory(self, sku_id, safety_stock, reorder_point, lead_time, 
                           order_qty, days=365):
        """
        Simulate inventory levels for a SKU with given parameters.
        
        Args:
            sku_id: SKU to simulate
            safety_stock: Safety stock level
            reorder_point: Reorder point
            lead_time: Lead time in days
            order_qty: Order quantity
            days: Number of days to simulate
            
        Returns:
            dict with simulation results
        """
        # Get demand distribution for this SKU
        stats = self.demand_stats[self.demand_stats['sku_id'] == sku_id]
        if len(stats) == 0:
            return None
        
        avg_demand = stats['avg_demand'].values[0]
        std_demand = stats['std_demand'].values[0]
        
        # Initialize simulation
        inventory = safety_stock + reorder_point  # Start with buffer
        pending_orders = []  # (arrival_day, quantity)
        
        stockout_days = 0
        overstock_days = 0
        total_carrying_cost = 0
        orders_placed = 0
        
        max_stock = reorder_point * 2  # Define overstock threshold
        
        for day in range(days):
            # Check for arriving orders
            arriving = [o for o in pending_orders if o[0] == day]
            for order in arriving:
                inventory += order[1]
            pending_orders = [o for o in pending_orders if o[0] > day]
            
            # Generate demand (normal distribution, non-negative)
            demand = max(0, int(np.random.normal(avg_demand, std_demand)))
            
            # Fulfill demand
            fulfilled = min(inventory, demand)
            inventory -= fulfilled
            
            # Check stockout
            if inventory == 0:
                stockout_days += 1
            
            # Check overstock
            if inventory > max_stock:
                overstock_days += 1
            
            # Calculate carrying cost (0.05% of inventory value per day)
            product = self.products[self.products['sku_id'] == sku_id]
            if len(product) > 0:
                unit_price = product['unit_price'].values[0]
                total_carrying_cost += inventory * unit_price * 0.0005
            
            # Check reorder point
            if inventory <= reorder_point and not any(o[0] > day for o in pending_orders):
                # Place order
                arrival_day = day + lead_time
                pending_orders.append((arrival_day, order_qty))
                orders_placed += 1
        
        # Calculate metrics
        instock_rate = 1 - (stockout_days / days)
        overstock_rate = overstock_days / days
        
        return {
            'sku_id': sku_id,
            'days_simulated': days,
            'safety_stock': safety_stock,
            'reorder_point': reorder_point,
            'lead_time': lead_time,
            'order_qty': order_qty,
            'stockout_days': stockout_days,
            'instock_rate': round(instock_rate * 100, 2),
            'overstock_days': overstock_days,
            'overstock_rate': round(overstock_rate * 100, 2),
            'total_carrying_cost': round(total_carrying_cost, 2),
            'orders_placed': orders_placed
        }


    def scenario_safety_stock_change(self, sku_id, change_pct):
        """
        Scenario 1: What if we change safety stock by X%?
        
        Args:
            sku_id: SKU to analyze
            change_pct: Percentage change (-50 to +100)
            
        Returns:
            Comparison of current vs new parameters
        """
        product = self.products[self.products['sku_id'] == sku_id]
        if len(product) == 0:
            return None
        
        current_ss = product['safety_stock'].values[0]
        current_rop = product['reorder_point'].values[0]
        lead_time = product['lead_time_days'].values[0]
        order_qty = product['min_order_qty'].values[0]
        
        new_ss = int(current_ss * (1 + change_pct / 100))
        new_rop = int(current_rop * (1 + change_pct / 100))
        
        # Simulate both scenarios
        current_result = self.simulate_inventory(
            sku_id, current_ss, current_rop, lead_time, order_qty
        )
        new_result = self.simulate_inventory(
            sku_id, new_ss, new_rop, lead_time, order_qty
        )
        
        return {
            'scenario': f'Safety Stock Change: {change_pct:+}%',
            'current': current_result,
            'proposed': new_result,
            'impact': {
                'stockout_change': new_result['stockout_days'] - current_result['stockout_days'],
                'instock_rate_change': new_result['instock_rate'] - current_result['instock_rate'],
                'carrying_cost_change': new_result['total_carrying_cost'] - current_result['total_carrying_cost']
            }
        }
    
    def scenario_lead_time_change(self, sku_id, lead_time_change):
        """
        Scenario 2: What if lead time increases/decreases by X days?
        
        Args:
            sku_id: SKU to analyze
            lead_time_change: Days to add/subtract
            
        Returns:
            Comparison of current vs new lead time
        """
        product = self.products[self.products['sku_id'] == sku_id]
        if len(product) == 0:
            return None
        
        safety_stock = product['safety_stock'].values[0]
        reorder_point = product['reorder_point'].values[0]
        current_lt = product['lead_time_days'].values[0]
        order_qty = product['min_order_qty'].values[0]
        
        new_lt = max(1, current_lt + lead_time_change)
        
        current_result = self.simulate_inventory(
            sku_id, safety_stock, reorder_point, current_lt, order_qty
        )
        new_result = self.simulate_inventory(
            sku_id, safety_stock, reorder_point, new_lt, order_qty
        )
        
        return {
            'scenario': f'Lead Time Change: {lead_time_change:+} days',
            'current_lead_time': current_lt,
            'new_lead_time': new_lt,
            'current': current_result,
            'proposed': new_result,
            'impact': {
                'stockout_change': new_result['stockout_days'] - current_result['stockout_days'],
                'instock_rate_change': new_result['instock_rate'] - current_result['instock_rate']
            }
        }


    def find_optimal_reorder_point(self, sku_id, target_service_level=0.95):
        """
        Scenario 3: Find optimal reorder point for target service level.
        
        Args:
            sku_id: SKU to optimize
            target_service_level: Target in-stock rate (0.95 = 95%)
            
        Returns:
            Optimal reorder point and simulation results
        """
        product = self.products[self.products['sku_id'] == sku_id]
        if len(product) == 0:
            return None
        
        safety_stock = product['safety_stock'].values[0]
        current_rop = product['reorder_point'].values[0]
        lead_time = product['lead_time_days'].values[0]
        order_qty = product['min_order_qty'].values[0]
        
        # Try different reorder points
        results = []
        for rop_multiplier in [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]:
            test_rop = int(current_rop * rop_multiplier)
            result = self.simulate_inventory(
                sku_id, safety_stock, test_rop, lead_time, order_qty
            )
            result['rop_multiplier'] = rop_multiplier
            results.append(result)
        
        results_df = pd.DataFrame(results)
        
        # Find minimum ROP that meets service level
        meeting_target = results_df[results_df['instock_rate'] >= target_service_level * 100]
        
        if len(meeting_target) > 0:
            optimal = meeting_target.sort_values('total_carrying_cost').iloc[0]
        else:
            optimal = results_df.sort_values('instock_rate', ascending=False).iloc[0]
        
        return {
            'scenario': f'Optimize ROP for {target_service_level*100}% Service Level',
            'current_rop': current_rop,
            'optimal_rop': int(optimal['reorder_point']),
            'optimal_instock_rate': optimal['instock_rate'],
            'optimal_carrying_cost': optimal['total_carrying_cost'],
            'all_results': results_df.to_dict('records')
        }
    
    def scenario_demand_change(self, sku_id, demand_change_pct):
        """
        Scenario 4: What if demand increases/decreases by X%?
        
        Args:
            sku_id: SKU to analyze
            demand_change_pct: Percentage change in demand
            
        Returns:
            Impact analysis
        """
        product = self.products[self.products['sku_id'] == sku_id]
        if len(product) == 0:
            return None
        
        stats = self.demand_stats[self.demand_stats['sku_id'] == sku_id]
        if len(stats) == 0:
            return None
        
        current_demand = stats['avg_demand'].values[0]
        new_demand = current_demand * (1 + demand_change_pct / 100)
        
        safety_stock = product['safety_stock'].values[0]
        reorder_point = product['reorder_point'].values[0]
        lead_time = product['lead_time_days'].values[0]
        
        # Calculate recommended new parameters
        recommended_ss = int(safety_stock * (1 + demand_change_pct / 100))
        recommended_rop = int(reorder_point * (1 + demand_change_pct / 100))
        
        return {
            'scenario': f'Demand Change: {demand_change_pct:+}%',
            'current_avg_demand': round(current_demand, 2),
            'projected_avg_demand': round(new_demand, 2),
            'current_parameters': {
                'safety_stock': safety_stock,
                'reorder_point': reorder_point
            },
            'recommended_parameters': {
                'safety_stock': recommended_ss,
                'reorder_point': recommended_rop
            },
            'recommendation': 'Increase safety stock and reorder point proportionally' if demand_change_pct > 0 else 'Consider reducing inventory levels'
        }


def run_scenario_analysis(sku_id=None):
    """
    Run comprehensive scenario analysis for a SKU.
    
    Args:
        sku_id: SKU to analyze (uses first SKU if None)
    """
    print("=" * 60)
    print("ReplenishIQ Scenario Modeling")
    print("=" * 60)
    
    simulator = ScenarioSimulator()
    
    if sku_id is None:
        sku_id = simulator.products['sku_id'].iloc[0]
    
    product = simulator.products[simulator.products['sku_id'] == sku_id].iloc[0]
    
    print(f"\nAnalyzing SKU: {sku_id}")
    print(f"Product: {product['product_name'][:50]}...")
    print(f"Category: {product['category']}")
    print(f"Current Parameters:")
    print(f"  Safety Stock: {product['safety_stock']}")
    print(f"  Reorder Point: {product['reorder_point']}")
    print(f"  Lead Time: {product['lead_time_days']} days")
    
    # Scenario 1: Safety Stock +20%
    print("\n" + "-" * 40)
    print("SCENARIO 1: Increase Safety Stock by 20%")
    print("-" * 40)
    result1 = simulator.scenario_safety_stock_change(sku_id, 20)
    if result1:
        print(f"Current In-Stock Rate: {result1['current']['instock_rate']}%")
        print(f"Proposed In-Stock Rate: {result1['proposed']['instock_rate']}%")
        print(f"Carrying Cost Change: ")
    
    # Scenario 2: Lead Time +3 days
    print("\n" + "-" * 40)
    print("SCENARIO 2: Lead Time Increases by 3 Days")
    print("-" * 40)
    result2 = simulator.scenario_lead_time_change(sku_id, 3)
    if result2:
        print(f"Current Lead Time: {result2['current_lead_time']} days")
        print(f"New Lead Time: {result2['new_lead_time']} days")
        print(f"In-Stock Rate Change: {result2['impact']['instock_rate_change']:+.2f}%")
        print(f"Additional Stockout Days: {result2['impact']['stockout_change']}")
    
    # Scenario 3: Optimize ROP
    print("\n" + "-" * 40)
    print("SCENARIO 3: Find Optimal Reorder Point (95% SLG)")
    print("-" * 40)
    result3 = simulator.find_optimal_reorder_point(sku_id, 0.95)
    if result3:
        print(f"Current ROP: {result3['current_rop']}")
        print(f"Optimal ROP: {result3['optimal_rop']}")
        print(f"Achievable In-Stock Rate: {result3['optimal_instock_rate']}%")
    
    # Scenario 4: Demand +30%
    print("\n" + "-" * 40)
    print("SCENARIO 4: Demand Increases by 30%")
    print("-" * 40)
    result4 = simulator.scenario_demand_change(sku_id, 30)
    if result4:
        print(f"Current Avg Demand: {result4['current_avg_demand']} units/day")
        print(f"Projected Demand: {result4['projected_avg_demand']} units/day")
        print(f"Recommended Safety Stock: {result4['recommended_parameters']['safety_stock']}")
        print(f"Recommended ROP: {result4['recommended_parameters']['reorder_point']}")
    
    print("\n" + "=" * 60)
    print("Scenario Analysis Complete!")
    print("=" * 60)
    
    return {
        'safety_stock_scenario': result1,
        'lead_time_scenario': result2,
        'rop_optimization': result3,
        'demand_scenario': result4
    }


if __name__ == "__main__":
    run_scenario_analysis()
