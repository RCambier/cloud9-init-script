# cloud9-init-script
This script helps quickly setup a Cloud9 instance by
- Setting an auto-shutdown cloudwatch alarm
- Installing conda
- Resizing the instance 

# Running it

When entering a new empty cloud9 environment, simply do
```bash
wget https://raw.githubusercontent.com/RCambier/cloud9-init-script/main/cloud9_init.py
python3 cloud9_init.py
```
The script will then ask you if you want to resize, if you want to install conda and if you want to setup an auto-shutdown alarm.
