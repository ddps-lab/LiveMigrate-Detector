import lightgbm as lgb
import time
import random


def generate_simple_data(n_samples, n_features):
    """간단한 랜덤 데이터 생성"""
    X = []
    y = []
    for i in range(n_samples):
        row = [random.random() for _ in range(n_features)]
        # 간단한 타겟 생성: 첫 번째 피처가 0.5보다 크면 1, 아니면 0
        target = 1 if row[0] > 0.5 else 0
        X.append(row)
        y.append(target)
    return X, y


def train_test_split(X, y, test_size=0.2):
    """간단한 train/test 분할"""
    n_test = int(len(X) * test_size)
    indices = list(range(len(X)))
    random.shuffle(indices)

    test_indices = indices[:n_test]
    train_indices = indices[n_test:]

    X_train = [X[i] for i in train_indices]
    y_train = [y[i] for i in train_indices]
    X_test = [X[i] for i in test_indices]
    y_test = [y[i] for i in test_indices]

    return X_train, X_test, y_train, y_test


def calculate_accuracy(y_true, y_pred):
    """정확도 계산"""
    correct = sum(1 for true, pred in zip(y_true, y_pred) if true == pred)
    return correct / len(y_true)


while True:
    print("=== Simple LightGBM Example ===", flush=True)

    # 간단한 데이터 생성
    X, y = generate_simple_data(1000, 5)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

    print(f"Training samples: {len(X_train)}", flush=True)
    print(f"Test samples: {len(X_test)}", flush=True)

    # LightGBM 데이터셋 생성
    train_data = lgb.Dataset(X_train, label=y_train)

    # 간단한 파라미터
    params = {
        'objective': 'binary',
        'metric': 'binary_logloss',
        'verbose': -1,
        'num_leaves': 10,
        'learning_rate': 0.1
    }

    # 모델 훈련
    model = lgb.train(
        params,
        train_data,
        num_boost_round=50
    )

    # 예측
    predictions = model.predict(X_test)
    binary_predictions = [1 if p > 0.5 else 0 for p in predictions]

    # 정확도 계산
    accuracy = calculate_accuracy(y_test, binary_predictions)

    print(f"Accuracy: {accuracy:.4f}", flush=True)
    print(f"Sample predictions: {predictions[:5]}", flush=True)
    print(f"Sample binary predictions: {binary_predictions[:5]}", flush=True)

    # 회귀 예제
    print("\n=== Simple Regression ===", flush=True)

    # 회귀용 데이터 생성
    X_reg = []
    y_reg = []
    for i in range(500):
        row = [random.random() for _ in range(3)]
        # 간단한 회귀 타겟: 모든 피처의 합
        target = sum(row) + random.random() * 0.1  # 약간의 노이즈 추가
        X_reg.append(row)
        y_reg.append(target)

    X_train_reg, X_test_reg, y_train_reg, y_test_reg = train_test_split(
        X_reg, y_reg)

    # 회귀 모델
    train_data_reg = lgb.Dataset(X_train_reg, label=y_train_reg)

    params_reg = {
        'objective': 'regression',
        'metric': 'rmse',
        'verbose': -1,
        'num_leaves': 10,
        'learning_rate': 0.1
    }

    reg_model = lgb.train(
        params_reg,
        train_data_reg,
        num_boost_round=50
    )

    # 회귀 예측
    reg_predictions = reg_model.predict(X_test_reg)

    # 간단한 MSE 계산
    mse = sum((true - pred) ** 2 for true,
              pred in zip(y_test_reg, reg_predictions)) / len(y_test_reg)

    print(f"MSE: {mse:.4f}", flush=True)
    print(f"Sample regression predictions: {reg_predictions[:3]}", flush=True)
    print(f"Sample true values: {y_test_reg[:3]}", flush=True)

    time.sleep(5)
