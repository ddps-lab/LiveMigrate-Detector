# sudo su

sed -i 's/"1";/"0";/g' /etc/apt/apt.conf.d/20auto-upgrades
systemctl stop unattended-upgrades.service
systemctl disable unattended-upgrades.service

add-apt-repository -y ppa:criu/ppa
apt update
NEEDRESTART_MODE=a apt install ubuntu-dbgsym-keyring
echo "Types: deb
URIs: http://ddebs.ubuntu.com/
Suites: $(lsb_release -cs) $(lsb_release -cs)-updates $(lsb_release -cs)-proposed 
Components: main restricted universe multiverse
Signed-by: /usr/share/keyrings/ubuntu-dbgsym-keyring.gpg" | \
sudo tee -a /etc/apt/sources.list.d/ddebs.sources
apt update
NEEDRESTART_MODE=a apt install -y git curl wget criu python3-pip python3-dbg build-essential gdb libssl-dev gpg-agent pkg-config libcurl4-openssl-dev cmake libssl3-dbgsym

pip3 install --upgrade pip setuptools packaging
pip3 install numpy dask psutil pyelftools stdlib-list pandas falcon xgboost scikit-learn llama-cpp-python ray
pip3 install Cython

git clone https://github.com/intelxed/xed.git
git clone https://github.com/intelxed/mbuild.git
cd xed
./mfile.py
export LD_LIBRARY_PATH=/home/ubuntu/xed/obj:$LD_LIBRARY_PATH
cd ..

git clone https://github.com/ddps-lab/LiveMigrate-Detector.git
cd LiveMigrate-Detector
git checkout fix
cd workload_instruction_analyzer/xedlib
gcc -shared -fPIC -o libxedwrapper.so xed_decoding.c -I/home/ubuntu/xed/include/public/xed/ -I/home/ubuntu/xed/obj/ -L/home/ubuntu/xed/obj/ -lxed
cd ../bytecode_tracking/exp_workloads/pku
python3 setup.py install
cd ../rand
gcc -shared -o librand.so -fPIC -mrdseed -mrdrnd rand.c
cd ../rsa
python3 setup.py install
cd ../sha
python3 setup.py install
cd ../llm
wget "https://huggingface.co/unsloth/Qwen3-0.6B-GGUF/resolve/main/Qwen3-0.6B-Q8_0.gguf?download=true" -O Qwen3-0.6B-Q8_0.gguf
cd ../xgboost
python3 xgb_download.py
cd ../int8dot
python3 setup.py install