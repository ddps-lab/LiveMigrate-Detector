import time
import random
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline


def generate_classification_data(n_samples, n_features, n_classes=2):
    """간단한 분류 데이터 생성"""
    X = []
    y = []
    for i in range(n_samples):
        row = [random.random() for _ in range(n_features)]
        # 간단한 분류 규칙
        if n_classes == 2:
            target = 1 if sum(row[:2]) > 1.0 else 0
        else:  # 3 클래스
            total = sum(row[:3])
            if total < 1.0:
                target = 0
            elif total < 2.0:
                target = 1
            else:
                target = 2
        X.append(row)
        y.append(target)
    return X, y


def generate_regression_data(n_samples, n_features):
    """간단한 회귀 데이터 생성"""
    X = []
    y = []
    for i in range(n_samples):
        row = [random.random() * 10 for _ in range(n_features)]
        # 간단한 선형 관계 + 노이즈
        target = sum(row[:3]) * 0.5 + random.random() * 2
        X.append(row)
        y.append(target)
    return X, y


def generate_clustering_data(n_samples, n_features):
    """간단한 클러스터링 데이터 생성"""
    X = []
    for i in range(n_samples):
        # 4개 클러스터 중심 주변에 데이터 생성
        cluster = i % 4
        if cluster == 0:
            row = [random.random() + 1, random.random() + 1] + [random.random()
                                                                for _ in range(n_features-2)]
        elif cluster == 1:
            row = [random.random() + 4, random.random() + 1] + [random.random()
                                                                for _ in range(n_features-2)]
        elif cluster == 2:
            row = [random.random() + 1, random.random() + 4] + [random.random()
                                                                for _ in range(n_features-2)]
        else:
            row = [random.random() + 4, random.random() + 4] + [random.random()
                                                                for _ in range(n_features-2)]
        X.append(row)
    return X


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


def calculate_mse(y_true, y_pred):
    """MSE 계산"""
    return sum((true - pred) ** 2 for true, pred in zip(y_true, y_pred)) / len(y_true)


def get_top_features(feature_importance, top_k=5):
    """상위 중요한 피처들의 인덱스 반환"""
    indexed_importance = [(i, importance)
                          for i, importance in enumerate(feature_importance)]
    sorted_features = sorted(
        indexed_importance, key=lambda x: x[1], reverse=True)
    return [idx for idx, _ in sorted_features[:top_k]]


while True:
    # Classification task
    print("=== Classification Task ===", flush=True)
    X_clf, y_clf = generate_classification_data(1000, 20, n_classes=3)
    X_train_clf, X_test_clf, y_train_clf, y_test_clf = train_test_split(
        X_clf, y_clf, test_size=0.2)

    # Random Forest Classifier
    rf_clf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf_clf.fit(X_train_clf, y_train_clf)
    rf_pred = rf_clf.predict(X_test_clf)
    rf_accuracy = calculate_accuracy(y_test_clf, rf_pred)
    print(f"Random Forest Accuracy: {rf_accuracy:.4f}", flush=True)

    # SVM Classifier with pipeline
    svm_pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('svm', SVC(kernel='rbf', C=1.0, random_state=42))
    ])
    svm_pipeline.fit(X_train_clf, y_train_clf)
    svm_pred = svm_pipeline.predict(X_test_clf)
    svm_accuracy = calculate_accuracy(y_test_clf, svm_pred)
    print(f"SVM Accuracy: {svm_accuracy:.4f}", flush=True)

    # Logistic Regression
    lr_clf = LogisticRegression(random_state=42, max_iter=1000)
    lr_clf.fit(X_train_clf, y_train_clf)
    lr_pred = lr_clf.predict(X_test_clf)
    lr_accuracy = calculate_accuracy(y_test_clf, lr_pred)
    print(f"Logistic Regression Accuracy: {lr_accuracy:.4f}", flush=True)

    # Regression task
    print("\n=== Regression Task ===", flush=True)
    X_reg, y_reg = generate_regression_data(1000, 10)
    X_train_reg, X_test_reg, y_train_reg, y_test_reg = train_test_split(
        X_reg, y_reg)

    # Random Forest Regressor
    rf_reg = RandomForestRegressor(n_estimators=100, random_state=42)
    rf_reg.fit(X_train_reg, y_train_reg)
    rf_reg_pred = rf_reg.predict(X_test_reg)
    rf_mse = calculate_mse(y_test_reg, rf_reg_pred)
    print(f"Random Forest MSE: {rf_mse:.4f}", flush=True)

    # Linear Regression
    lr_reg = LinearRegression()
    lr_reg.fit(X_train_reg, y_train_reg)
    lr_reg_pred = lr_reg.predict(X_test_reg)
    lr_mse = calculate_mse(y_test_reg, lr_reg_pred)
    print(f"Linear Regression MSE: {lr_mse:.4f}", flush=True)

    # Clustering task
    print("\n=== Clustering Task ===", flush=True)
    X_cluster = generate_clustering_data(300, 4)

    # K-Means clustering
    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(X_cluster)

    # 간단한 실루엣 스코어 대신 클러스터 정보만 출력
    unique_labels = set(cluster_labels)
    print(f"Number of clusters found: {len(unique_labels)}", flush=True)
    print(
        f"Cluster centers shape: {kmeans.cluster_centers_.shape}", flush=True)

    # Feature importance from Random Forest
    feature_importance = rf_clf.feature_importances_
    top_features = get_top_features(feature_importance, 5)
    top_scores = [feature_importance[i] for i in top_features]
    print(f"\nTop 5 important features: {top_features}", flush=True)
    print(f"Their importance scores: {top_scores}", flush=True)

    time.sleep(5)
