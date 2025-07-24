import tensorflow as tf
import numpy as np
import time

while True:
    model = tf.keras.Sequential([
        tf.keras.layers.Dense(50, activation='relu', input_shape=(10,)),
        tf.keras.layers.Dense(20, activation='relu'),
        tf.keras.layers.Dense(1)
    ])

    model.compile(optimizer='adam', loss='mse', metrics=['mae'])

    X_train = np.random.randn(100, 10)
    y_train = np.random.randn(100, 1)

    history = model.fit(X_train, y_train, epochs=20, verbose=0)

    final_loss = history.history['loss'][-1]
    final_mae = history.history['mae'][-1]
    print(f"Final loss: {final_loss:.4f}, MAE: {final_mae:.4f}", flush=True)

    X_test = np.random.randn(5, 10)
    predictions = model.predict(X_test, verbose=0)
    print(f"Test predictions: {predictions.flatten().tolist()}", flush=True)

    conv_model = tf.keras.Sequential([
        tf.keras.layers.Conv2D(
            32, (3, 3), activation='relu', input_shape=(28, 28, 1)),
        tf.keras.layers.MaxPooling2D((2, 2)),
        tf.keras.layers.Conv2D(64, (3, 3), activation='relu'),
        tf.keras.layers.GlobalAveragePooling2D(),
        tf.keras.layers.Dense(10, activation='softmax')
    ])

    dummy_input = np.random.randn(1, 28, 28, 1)
    conv_output = conv_model.predict(dummy_input, verbose=0)
    print(f"Conv model output shape: {conv_output.shape}", flush=True)

    time.sleep(5)
