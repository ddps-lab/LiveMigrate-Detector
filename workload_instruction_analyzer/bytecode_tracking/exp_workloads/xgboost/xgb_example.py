import numpy as np
from sklearn.datasets import fetch_openml
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
# from xgboost import XGBClassifier
import xgboost as xgb

import time

# MNIST 데이터셋 불러오기
mnist = fetch_openml('mnist_784', version=1, parser='auto')  # parser 매개변수 설정
X = mnist.data
y = mnist.target.astype(np.int64)  # 정수형으로 변환

# 훈련 데이터와 테스트 데이터로 분할
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# 데이터 표준화
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

# XGBoost 모델 생성 및 하이퍼파라미터 설정
model = xgb.XGBClassifier(
    use_label_encoder=False, 
    eval_metric='mlogloss', 
    n_estimators=100,        # 부스팅 라운드(트리) 수
    max_depth=6,             # 트리의 최대 깊이
    learning_rate=0.1,       # 학습률
    subsample=0.8,           # 부스팅 라운드마다 사용할 훈련 데이터의 비율
    colsample_bytree=0.8,    # 각 트리에서 사용할 피처의 비율
    gamma=0,                 # 최소 손실 감소
    reg_alpha=0,             # L1 정규화 항의 가중치
    reg_lambda=1             # L2 정규화 항의 가중치
)

# 학습 과정 중 진행 상황을 출력하도록 설정
eval_set = [(X_train, y_train), (X_test, y_test)]
model.fit(X_train, y_train, eval_set=eval_set, verbose=True, early_stopping_rounds=5)

# 예측
y_pred = model.predict(X_test)

# 성능 평가
accuracy = accuracy_score(y_test, y_pred)
conf_matrix = confusion_matrix(y_test, y_pred)
class_report = classification_report(y_test, y_pred)

print("Accuracy:", accuracy)
print("Confusion Matrix:\n", conf_matrix)
print("Classification Report:\n", class_report)

time.sleep(10000)