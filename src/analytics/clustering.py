"""
ReplenishIQ SKU Clustering Module
Segments SKUs into groups based on demand patterns and characteristics.

Uses K-Means clustering with features:
- Average daily demand
- Demand variability (coefficient of variation)
- Revenue contribution
- Stockout frequency
- Inventory turns
"""

import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
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
    
    return products, sales, inventory

def calculate_sku_features(products, sales, inventory):
    """
    Calculate clustering features for each SKU.
    
    Features:
    1. avg_daily_demand - Average units sold per day
    2. demand_cv - Coefficient of variation (std/mean) - measures variability
    3. total_revenue - Total revenue generated
    4. stockout_rate - % of days with stockout
    5. avg_inventory - Average inventory level
    6. inventory_turns - How fast inventory moves
    """
    
    # Sales metrics
    sales_agg = sales.groupby('sku_id').agg({
        'units_sold': ['mean', 'std', 'sum'],
        'revenue': 'sum'
    }).reset_index()
    sales_agg.columns = ['sku_id', 'avg_daily_demand', 'demand_std', 'total_units', 'total_revenue']
    
    # Calculate coefficient of variation (CV = std/mean)
    sales_agg['demand_cv'] = sales_agg['demand_std'] / sales_agg['avg_daily_demand'].replace(0, np.nan)
    sales_agg['demand_cv'] = sales_agg['demand_cv'].fillna(0)
    
    # Inventory metrics
    inv_agg = inventory.groupby('sku_id').agg({
        'on_hand_qty': 'mean',
        'stockout_flag': 'mean',  # This gives us the rate
        'overstock_flag': 'mean'
    }).reset_index()
    inv_agg.columns = ['sku_id', 'avg_inventory', 'stockout_rate', 'overstock_rate']
    
    # Merge all features
    features = products[['sku_id', 'category', 'unit_price']].merge(sales_agg, on='sku_id', how='left')
    features = features.merge(inv_agg, on='sku_id', how='left')
    
    # Calculate inventory turns
    features['inventory_turns'] = features['total_units'] / features['avg_inventory'].replace(0, np.nan)
    features['inventory_turns'] = features['inventory_turns'].fillna(0)
    
    # Fill any remaining NaN
    features = features.fillna(0)
    
    return features


class SKUClusteringEngine:
    """
    K-Means clustering engine for SKU segmentation.
    """
    
    def __init__(self, n_clusters=4):
        """
        Args:
            n_clusters: Number of clusters (default 4 for A/B/C/D classification)
        """
        self.n_clusters = n_clusters
        self.model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        self.scaler = StandardScaler()
        self.feature_cols = [
            'avg_daily_demand', 
            'demand_cv', 
            'total_revenue', 
            'stockout_rate',
            'inventory_turns'
        ]
        self.cluster_labels = None
        
    def fit_predict(self, features_df):
        """
        Fit clustering model and predict cluster assignments.
        
        Args:
            features_df: DataFrame with SKU features
            
        Returns:
            DataFrame with cluster assignments
        """
        # Prepare feature matrix
        X = features_df[self.feature_cols].values
        X_scaled = self.scaler.fit_transform(X)
        
        # Fit and predict
        clusters = self.model.fit_predict(X_scaled)
        
        # Add cluster labels to dataframe
        result = features_df.copy()
        result['cluster'] = clusters
        
        # Calculate silhouette score (cluster quality metric)
        self.silhouette = silhouette_score(X_scaled, clusters)
        
        # Assign meaningful labels based on cluster characteristics
        result = self._assign_cluster_labels(result)
        
        return result
    
    def _assign_cluster_labels(self, df):
        """
        Assign meaningful labels to clusters based on characteristics.
        
        Labels:
        - A (High Value): High revenue, high demand
        - B (Growth): Medium revenue, high variability
        - C (Stable): Low-medium revenue, low variability
        - D (Low Priority): Low revenue, low demand
        """
        # Calculate cluster means
        cluster_stats = df.groupby('cluster').agg({
            'total_revenue': 'mean',
            'avg_daily_demand': 'mean',
            'demand_cv': 'mean',
            'stockout_rate': 'mean'
        }).reset_index()
        
        # Rank clusters by revenue
        cluster_stats['revenue_rank'] = cluster_stats['total_revenue'].rank(ascending=False)
        
        # Create label mapping
        label_map = {}
        labels = ['A', 'B', 'C', 'D']
        for i, row in cluster_stats.sort_values('revenue_rank').iterrows():
            idx = int(row['revenue_rank']) - 1
            if idx < len(labels):
                label_map[row['cluster']] = labels[idx]
            else:
                label_map[row['cluster']] = 'D'
        
        df['cluster_label'] = df['cluster'].map(label_map)
        self.cluster_labels = label_map
        
        return df
    
    def get_cluster_summary(self, df):
        """
        Generate summary statistics for each cluster.
        """
        summary = df.groupby('cluster_label').agg({
            'sku_id': 'count',
            'avg_daily_demand': 'mean',
            'demand_cv': 'mean',
            'total_revenue': ['sum', 'mean'],
            'stockout_rate': 'mean',
            'inventory_turns': 'mean'
        }).round(2)
        
        summary.columns = [
            'sku_count', 'avg_demand', 'avg_variability',
            'total_revenue', 'avg_revenue', 'avg_stockout_rate', 'avg_turns'
        ]
        
        return summary.sort_index()


def find_optimal_clusters(features_df, max_clusters=8):
    """
    Find optimal number of clusters using silhouette score.
    
    Args:
        features_df: DataFrame with SKU features
        max_clusters: Maximum clusters to try
        
    Returns:
        dict with scores for each k
    """
    feature_cols = [
        'avg_daily_demand', 
        'demand_cv', 
        'total_revenue', 
        'stockout_rate',
        'inventory_turns'
    ]
    
    X = features_df[feature_cols].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    scores = {}
    for k in range(2, max_clusters + 1):
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X_scaled)
        score = silhouette_score(X_scaled, labels)
        scores[k] = score
    
    return scores


def run_clustering(n_clusters=4, output_file='sku_clusters.csv'):
    """
    Run full clustering pipeline.
    
    Args:
        n_clusters: Number of clusters
        output_file: Output filename
    """
    print("=" * 60)
    print("ReplenishIQ SKU Clustering")
    print("=" * 60)
    
    # Load data
    print("\nLoading data...")
    products, sales, inventory = load_data()
    
    # Calculate features
    print("Calculating SKU features...")
    features = calculate_sku_features(products, sales, inventory)
    print(f"  Total SKUs: {len(features)}")
    
    # Run clustering
    print(f"\nRunning K-Means clustering (k={n_clusters})...")
    engine = SKUClusteringEngine(n_clusters=n_clusters)
    clustered = engine.fit_predict(features)
    
    print(f"  Silhouette Score: {engine.silhouette:.3f}")
    print("  (Score ranges from -1 to 1, higher is better)")
    
    # Print summary
    print("\n" + "-" * 40)
    print("Cluster Summary:")
    print("-" * 40)
    summary = engine.get_cluster_summary(clustered)
    print(summary.to_string())
    
    # Cluster descriptions
    print("\n" + "-" * 40)
    print("Cluster Descriptions:")
    print("-" * 40)
    descriptions = {
        'A': 'HIGH VALUE - Top revenue generators, prioritize availability',
        'B': 'GROWTH - Medium revenue, monitor closely for trends',
        'C': 'STABLE - Consistent demand, standard replenishment',
        'D': 'LOW PRIORITY - Low revenue, consider reducing inventory'
    }
    for label in sorted(clustered['cluster_label'].unique()):
        count = len(clustered[clustered['cluster_label'] == label])
        print(f"  Cluster {label}: {count} SKUs - {descriptions.get(label, 'N/A')}")
    
    # Save results
    project_root = get_project_root()
    output_path = os.path.join(project_root, 'data', 'processed', output_file)
    
    # Select columns to save
    output_cols = [
        'sku_id', 'category', 'unit_price', 'avg_daily_demand', 
        'demand_cv', 'total_revenue', 'stockout_rate', 'inventory_turns',
        'cluster', 'cluster_label'
    ]
    clustered[output_cols].to_csv(output_path, index=False)
    
    print(f"\nResults saved to: {output_path}")
    
    print("\n" + "=" * 60)
    print("Clustering complete!")
    print("=" * 60)
    
    return clustered, engine


if __name__ == "__main__":
    run_clustering(n_clusters=4)
