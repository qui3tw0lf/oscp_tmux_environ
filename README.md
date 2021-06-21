# oscp_tmux_environ

Setup a tmux environment for targets like on HackTheBox, Vulnhub, TryHackme. It creates a directory for the target and then sets up some windows in newly created tmux session to perform basic operations like a _nmap scan_ or a _ping test_ to ensure the machine is up.

Settings can be modified using the _tmux.ini_ file. 

It contains all the basic configurations including:
- Window list
  - commands list
  - run_once option
 
- General config
  - add ping window
  - setup nmap commands

#### Usage
```bash
python3 main.py -t [machine_name]:[machine_ip] -d [machine_dir]
```

#### Options
```
-t  :   machine_name:machine_ip
-d  :   machine directory
```

#### Examples
```bash
python3 main.py -t machine1:127.0.0.1 -d /tmp/machine1
python3 main.py -t machine1:127.0.0.1       # Directory defaults to the current working directory
```
