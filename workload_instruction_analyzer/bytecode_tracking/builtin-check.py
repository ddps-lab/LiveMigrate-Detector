import sys

# 특정 모듈 이름
module_name = "time"

# 내장 모듈인지 확인
if module_name in sys.builtin_module_names:
    print(f"{module_name} is a built-in module.")
else:
    print(f"{module_name} is not a built-in module.")
