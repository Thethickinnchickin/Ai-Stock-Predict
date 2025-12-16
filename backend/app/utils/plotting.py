import plotly.graph_objects as go
import numpy as np

def plot_predictions(symbol, history_prices, predicted_prices, target_price=None):
    """
    Plots historical prices vs predicted prices, with optional target line.
    Highlights days where prediction hit/fail target.
    
    Args:
        symbol (str): Stock symbol
        history_prices (list[float]): Historical prices
        predicted_prices (list[float]): Predicted prices for next N days
        target_price (float, optional): Target price to highlight hits
    """
    N_history = len(history_prices)
    N_pred = len(predicted_prices)
    
    # X-axis: time indices
    x_history = list(range(N_history))
    x_pred = list(range(N_history, N_history + N_pred))
    
    fig = go.Figure()
    
    # Historical prices
    fig.add_trace(go.Scatter(
        x=x_history,
        y=history_prices,
        mode='lines+markers',
        name='Historical',
        line=dict(color='blue')
    ))
    
    # Predicted prices
    fig.add_trace(go.Scatter(
        x=x_pred,
        y=predicted_prices,
        mode='lines+markers',
        name='Predicted',
        line=dict(color='orange', dash='dot')
    ))
    
    # Confidence interval (simple +/- 2% for demonstration)
    lower = [p * 0.98 for p in predicted_prices]
    upper = [p * 1.02 for p in predicted_prices]
    fig.add_trace(go.Scatter(
        x=x_pred + x_pred[::-1],
        y=upper + lower[::-1],
        fill='toself',
        fillcolor='rgba(255,165,0,0.2)',
        line=dict(color='rgba(255,165,0,0)'),
        hoverinfo="skip",
        showlegend=True,
        name="Confidence Interval"
    ))
    
    # Target line and hits/fails
    if target_price is not None:
        hits_x, hits_y = [], []
        fails_x, fails_y = [], []
        last_price = history_prices[-1]
        for i, p in enumerate(predicted_prices):
            if (target_price >= last_price and p >= target_price) or \
               (target_price < last_price and p <= target_price):
                hits_x.append(N_history + i)
                hits_y.append(p)
            else:
                fails_x.append(N_history + i)
                fails_y.append(p)
                
        # Highlight hits
        fig.add_trace(go.Scatter(
            x=hits_x, y=hits_y,
            mode='markers',
            name='Hit Target',
            marker=dict(color='green', size=10, symbol='star')
        ))
        # Highlight fails
        fig.add_trace(go.Scatter(
            x=fails_x, y=fails_y,
            mode='markers',
            name='Missed Target',
            marker=dict(color='red', size=10, symbol='x')
        ))
    
    fig.update_layout(
        title=f"{symbol} Prediction vs Actual",
        xaxis_title="Time Steps",
        yaxis_title="Price",
        template="plotly_dark"
    )
    
    fig.show()
