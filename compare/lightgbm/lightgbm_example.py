import lightgbm as lgb
import numpy as np
import time
from sklearn.datasets import make_classification, make_regression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_squared_error, log_loss

while True:
    # Classification with LightGBM
    print("=== LightGBM Classification ===", flush=True)
    X_clf, y_clf = make_classification(n_samples=2000, n_features=30, n_classes=2,
                                       n_redundant=5, n_informative=20, random_state=42)
    X_train_clf, X_test_clf, y_train_clf, y_test_clf = train_test_split(
        X_clf, y_clf, test_size=0.2, random_state=42)

    # Create LightGBM datasets
    train_data_clf = lgb.Dataset(X_train_clf, label=y_train_clf)
    valid_data_clf = lgb.Dataset(
        X_test_clf, label=y_test_clf, reference=train_data_clf)

    # Classification parameters
    params_clf = {
        'objective': 'binary',
        'metric': ['binary_logloss', 'binary_error'],
        'boosting_type': 'gbdt',
        'num_leaves': 31,
        'learning_rate': 0.05,
        'feature_fraction': 0.9,
        'bagging_fraction': 0.8,
        'bagging_freq': 5,
        'verbose': -1,
        'random_state': 42
    }

    # Train classification model
    clf_model = lgb.train(
        params_clf,
        train_data_clf,
        valid_sets=[train_data_clf, valid_data_clf],
        valid_names=['train', 'eval'],
        num_boost_round=100,
        callbacks=[lgb.early_stopping(
            stopping_rounds=10), lgb.log_evaluation(0)]
    )

    # Make predictions
    y_pred_clf = clf_model.predict(
        X_test_clf, num_iteration=clf_model.best_iteration)
    y_pred_binary = (y_pred_clf > 0.5).astype(int)

    clf_accuracy = accuracy_score(y_test_clf, y_pred_binary)
    clf_logloss = log_loss(y_test_clf, y_pred_clf)

    print(f"Classification Accuracy: {clf_accuracy:.4f}", flush=True)
    print(f"Classification Log Loss: {clf_logloss:.4f}", flush=True)
    print(f"Best iteration: {clf_model.best_iteration}", flush=True)

    # Feature importance for classification
    feature_importance_clf = clf_model.feature_importance(
        importance_type='gain')
    top_features_clf = np.argsort(feature_importance_clf)[-5:][::-1]
    print(
        f"Top 5 important features (clf): {top_features_clf.tolist()}", flush=True)

    # Regression with LightGBM
    print("\n=== LightGBM Regression ===", flush=True)
    X_reg, y_reg = make_regression(
        n_samples=2000, n_features=20, noise=0.1, random_state=42)
    X_train_reg, X_test_reg, y_train_reg, y_test_reg = train_test_split(
        X_reg, y_reg, test_size=0.2, random_state=42)

    # Create LightGBM datasets for regression
    train_data_reg = lgb.Dataset(X_train_reg, label=y_train_reg)
    valid_data_reg = lgb.Dataset(
        X_test_reg, label=y_test_reg, reference=train_data_reg)

    # Regression parameters
    params_reg = {
        'objective': 'regression',
        'metric': 'rmse',
        'boosting_type': 'gbdt',
        'num_leaves': 31,
        'learning_rate': 0.05,
        'feature_fraction': 0.9,
        'bagging_fraction': 0.8,
        'bagging_freq': 5,
        'verbose': -1,
        'random_state': 42
    }

    # Train regression model
    reg_model = lgb.train(
        params_reg,
        train_data_reg,
        valid_sets=[train_data_reg, valid_data_reg],
        valid_names=['train', 'eval'],
        num_boost_round=100,
        callbacks=[lgb.early_stopping(
            stopping_rounds=10), lgb.log_evaluation(0)]
    )

    # Make regression predictions
    y_pred_reg = reg_model.predict(
        X_test_reg, num_iteration=reg_model.best_iteration)
    reg_mse = mean_squared_error(y_test_reg, y_pred_reg)
    reg_rmse = np.sqrt(reg_mse)

    print(f"Regression MSE: {reg_mse:.4f}", flush=True)
    print(f"Regression RMSE: {reg_rmse:.4f}", flush=True)
    print(f"Best iteration: {reg_model.best_iteration}", flush=True)

    # Feature importance for regression
    feature_importance_reg = reg_model.feature_importance(
        importance_type='gain')
    top_features_reg = np.argsort(feature_importance_reg)[-5:][::-1]
    print(
        f"Top 5 important features (reg): {top_features_reg.tolist()}", flush=True)

    # Multi-class classification
    print("\n=== LightGBM Multi-class Classification ===", flush=True)
    X_multi, y_multi = make_classification(n_samples=1500, n_features=15, n_classes=3,
                                           n_redundant=0, n_informative=10, random_state=42)
    X_train_multi, X_test_multi, y_train_multi, y_test_multi = train_test_split(
        X_multi, y_multi, test_size=0.2, random_state=42)

    # Multi-class parameters
    params_multi = {
        'objective': 'multiclass',
        'num_class': 3,
        'metric': 'multi_logloss',
        'boosting_type': 'gbdt',
        'num_leaves': 31,
        'learning_rate': 0.05,
        'feature_fraction': 0.9,
        'verbose': -1,
        'random_state': 42
    }

    train_data_multi = lgb.Dataset(X_train_multi, label=y_train_multi)
    valid_data_multi = lgb.Dataset(
        X_test_multi, label=y_test_multi, reference=train_data_multi)

    multi_model = lgb.train(
        params_multi,
        train_data_multi,
        valid_sets=[train_data_multi, valid_data_multi],
        valid_names=['train', 'eval'],
        num_boost_round=100,
        callbacks=[lgb.early_stopping(
            stopping_rounds=10), lgb.log_evaluation(0)]
    )

    y_pred_multi = multi_model.predict(
        X_test_multi, num_iteration=multi_model.best_iteration)
    y_pred_multi_class = np.argmax(y_pred_multi, axis=1)
    multi_accuracy = accuracy_score(y_test_multi, y_pred_multi_class)

    print(f"Multi-class Accuracy: {multi_accuracy:.4f}", flush=True)
    print(f"Prediction probabilities shape: {y_pred_multi.shape}", flush=True)

    time.sleep(5)
