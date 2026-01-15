import asyncio
import os
from datetime import datetime
from app.models.predictor import predictor
from app.config.settings import settings


async def main():
    results = await predictor.backtest(val_size=200)
    if not results:
        print("No backtest results (insufficient data).")
        return

    print("Backtest Results (log-return)")
    print(f"MAE model:     {results['mae_model']:.6f}")
    print(f"MAE baseline:  {results['mae_baseline']:.6f}")
    print(f"Directional accuracy model:    {results['directional_accuracy_model']:.3f}")
    print(f"Directional accuracy baseline: {results['directional_accuracy_baseline']:.3f}")
    print(f"Validation size: {results['validation_size']}")

    log_path = settings.BACKTEST_LOG_PATH
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = (
        f"{timestamp} | MAE_model={results['mae_model']:.6f} "
        f"MAE_baseline={results['mae_baseline']:.6f} "
        f"DirAcc_model={results['directional_accuracy_model']:.3f} "
        f"DirAcc_baseline={results['directional_accuracy_baseline']:.3f} "
        f"Val={results['validation_size']}\n"
    )
    with open(log_path, "a", encoding="utf-8") as handle:
        handle.write(line)


if __name__ == "__main__":
    asyncio.run(main())
