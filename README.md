````script
cd ~ && 
rm -rf RaspController backend_payload.zip && 
wget -O backend_payload.zip https://raw.githubusercontent.com/AirysDark/RaspLink/main/backend_payload.zip && 
unzip -o backend_payload.zip && 
cd RaspController && 
python3 install.py && 
nohup ./start_api.sh > logs/api.log 2>&1 &
````
