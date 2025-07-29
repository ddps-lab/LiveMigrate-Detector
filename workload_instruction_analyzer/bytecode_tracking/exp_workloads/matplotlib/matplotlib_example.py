import matplotlib.pyplot as plt
import numpy as np
import time
import io
import base64

while True:
    x = np.linspace(0, 10, 100)
    y1 = np.sin(x + time.time())
    y2 = np.cos(x + time.time())

    plt.figure(figsize=(10, 6))
    plt.plot(x, y1, label='sin(x)', linewidth=2)
    plt.plot(x, y2, label='cos(x)', linewidth=2)
    plt.xlabel('X values')
    plt.ylabel('Y values')
    plt.title(f'Sine and Cosine Waves - {time.strftime("%H:%M:%S")}')
    plt.legend()
    plt.grid(True)

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plot_data = base64.b64encode(buffer.read()).decode()

    plt.close()

    print(f"Plot generated at {time.strftime('%H:%M:%S')}", flush=True)
    print(f"Plot data size: {len(plot_data)} bytes", flush=True)

    hist_data = np.random.normal(100, 15, 1000)
    plt.figure(figsize=(8, 6))
    plt.hist(hist_data, bins=30, alpha=0.7, color='blue')
    plt.title('Random Normal Distribution')
    plt.xlabel('Value')
    plt.ylabel('Frequency')
    plt.close()

    print("Histogram generated", flush=True)

    time.sleep(5)
