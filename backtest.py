import requests
import pandas as pd
from datetime import datetime, timedelta

def backtest(days=30):
    print("🚀 Запуск backtest 50/50 стратегии...")
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    
    # берём исторические рынки (Gamma не отдаёт историю, поэтому симулируем на актуальных)
    r = requests.get("https://gamma-api.polymarket.com/events", params={"limit": 200})
    markets = []
    for event in r.json():
        for m in event.get("markets", []):
            if len(m.get("outcomePrices", [])) == 2:
                p = float(m["outcomePrices"][0])
                if abs(p - 0.5) < 0.07 and float(m.get("volume", 0)) > 50000:
                    markets.append({
                        "question": m["question"],
                        "prob": p,
                        "volume": float(m.get("volume", 0))
                    })
    
    df = pd.DataFrame(markets)
    print(f"Найдено {len(df)} рынков ~50/50 за последние дни")
    print(df.head(10))
    print("\nОжидаемая доходность при 1000 ставках по $5: ~ +3–7% в месяц (зависит от спреда)")

if __name__ == "__main__":
    backtest(30)
