#!/usr/bin/env python3
"""
Risk-Aware Multi-Asset RL Trading System
=========================================
Main entry point. Runs the full pipeline:
1. Data preparation
2. Agent training (PPO + SAC ensemble)
3. Backtesting evaluation
4. Dashboard data generation
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from training.pipeline import TrainingPipeline, run_training
from config.settings import CONFIG


def main():
    pipeline, results, dashboard_data = run_training()

    print("\n" + "=" * 60)
    print("SYSTEM SUMMARY")
    print("=" * 60)
    print(f"  Assets:          {CONFIG.data.tickers}")
    print(f"  Benchmark:       {CONFIG.data.benchmark}")
    print(f"  Initial Capital: ${CONFIG.trading.initial_capital:,.0f}")
    print(f"  Reward Weights:  w1={CONFIG.reward.w1}, w2={CONFIG.reward.w2}, "
          f"w3={CONFIG.reward.w3}, w4={CONFIG.reward.w4}")
    print(f"\n  Test Performance:")
    for k, v in results.get("test", {}).items():
        print(f"    {k:25s}: {v}")

    print(f"\n  Dashboard data: output/dashboard_data.json")
    print("  Launch dashboard: open the React dashboard artifact")
    print("\nDone!")


if __name__ == "__main__":
    main()
