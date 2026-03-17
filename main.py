"""
ReplenishIQ - Main Entry Point
Runs the complete analytics pipeline.
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    print("=" * 60)
    print("ReplenishIQ - Replenishment Parameter Optimization Engine")
    print("=" * 60)
    
    print("\nStep 1: Data Generation")
    print("-" * 40)
    from data.data_generation import main as generate_data
    generate_data()
    
    print("\n\nStep 2: Data Validation")
    print("-" * 40)
    from data.validate_data import main as validate_data
    validate_data()
    
    print("\n\nPipeline complete!")
    print("Next steps:")
    print("  1. Set up PostgreSQL and run: psql replenishiq < sql/schema.sql")
    print("  2. Configure .env with database credentials")
    print("  3. Run: python src/data/load_data.py")
    print("  4. Continue with Phase 2 (SQL Analysis)")

if __name__ == "__main__":
    main()
