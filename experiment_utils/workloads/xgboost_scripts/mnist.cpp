#include <iostream>
#include <vector>
#include <fstream>
#include <sstream>
#include <string>
#include <cmath>
#include <algorithm>
#include <dmlc/logging.h>
#include <dmlc/timer.h>
#include <xgboost/c_api.h>

#define safe_xgboost(call) { int err = (call); if (err != 0) { std::cerr << "XGBoost Error: " << XGBGetLastError() << std::endl; exit(1); } }

void load_csv(const char* filename, std::vector<float>& data, std::vector<float>& labels, int& n, int& m) {
    std::ifstream file(filename);
    std::string line;
    while (std::getline(file, line)) {
        std::istringstream iss(line);
        std::string val;
        int j = 0;
        while (std::getline(iss, val, ',')) {
            if (j == 0) {
                labels.push_back(std::stof(val));
            } else {
                data.push_back(std::stof(val)/255.0);  // Scaling pixel values to [0, 1]
            }
            ++j;
        }
        if (m == 0) m = j - 1;
        ++n;
    }
}

int main() {
    while(1){
        std::vector<float> train_data;
        std::vector<float> train_labels;
        int n_train = 0, m_train = 0;
        load_csv("/home/ubuntu/migration_test/xgboost_scripts/mnist_train.csv", train_data, train_labels, n_train, m_train);

        std::vector<float> test_data;
        std::vector<float> test_labels;
        int n_test = 0, m_test = 0;
        load_csv("/home/ubuntu/migration_test/xgboost_scripts/mnist_test.csv", test_data, test_labels, n_test, m_test);

        DMatrixHandle h_train;
        safe_xgboost(XGDMatrixCreateFromMat(train_data.data(), n_train, m_train, NAN, &h_train));
        safe_xgboost(XGDMatrixSetFloatInfo(h_train, "label", train_labels.data(), n_train));

        DMatrixHandle h_test;
        safe_xgboost(XGDMatrixCreateFromMat(test_data.data(), n_test, m_test, NAN, &h_test));
        safe_xgboost(XGDMatrixSetFloatInfo(h_test, "label", test_labels.data(), n_test));

        // Set parameters
        BoosterHandle h_booster;
        safe_xgboost(XGBoosterCreate(&h_train, 1, &h_booster));
        safe_xgboost(XGBoosterSetParam(h_booster, "booster", "gbtree"));
        safe_xgboost(XGBoosterSetParam(h_booster, "objective", "multi:softprob"));
        safe_xgboost(XGBoosterSetParam(h_booster, "num_class", "10"));
        safe_xgboost(XGBoosterSetParam(h_booster, "max_depth", "3"));
        safe_xgboost(XGBoosterSetParam(h_booster, "eta", "0.1"));
        safe_xgboost(XGBoosterSetParam(h_booster, "min_child_weight", "1"));
        safe_xgboost(XGBoosterSetParam(h_booster, "subsample", "0.5"));
        safe_xgboost(XGBoosterSetParam(h_booster, "colsample_bytree", "1"));
        safe_xgboost(XGBoosterSetParam(h_booster, "num_parallel_tree", "1"));

        int n_trees = 100;
        for (int iter = 0; iter < n_trees; ++iter) {
            safe_xgboost(XGBoosterUpdateOneIter(h_booster, iter, h_train));
            
            const char* eval_names[] = {"train"};
            DMatrixHandle eval_data[] = {h_train};
            const char *out_result; // 평가 결과를 저장할 문자열 포인터
            safe_xgboost(XGBoosterEvalOneIter(h_booster, iter, eval_data, eval_names, 1, &out_result));
            std::cout << "Iteration " << iter << ": " << out_result << std::endl;
        }

        // Make prediction and evaluate
        bst_ulong out_len;
        const float *out_result;
        safe_xgboost(XGBoosterPredict(h_booster, h_test, 0, 0, 0, &out_len, &out_result));

        int correct = 0;
        for (size_t i = 0; i < out_len; i += 10) {
            auto max_it = std::max_element(out_result + i, out_result + i + 10);
            if (static_cast<int>(max_it - (out_result + i)) == static_cast<int>(test_labels[i / 10])) {
                ++correct;
            }
        }

        std::cout << "Accuracy: " << static_cast<float>(correct) / n_test << std::endl;

        // Free memory
        safe_xgboost(XGDMatrixFree(h_train));
        safe_xgboost(XGDMatrixFree(h_test));
        safe_xgboost(XGBoosterFree(h_booster));
    }

    return 0;
}