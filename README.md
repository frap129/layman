# Simple master and stack layout script
```
| ------ | ----- |
|        |       |
| Master | Stack |
|        |       |
| ------ | ----- |
```

* auto split 2nd window on workspace level to provide a vertical stack

* put new windows at the end of the workspace tree

* swap focused window with the master window (first window on current workspace tree) [i3-swap-master.py](./i3-swap-master.py)

* works independant from i3 state (no permanent marks required to keep track)

* if master windows disappears, get new master window from stack (does only really work if you don't break the initial layout)

![master-layout](./i3-master-layout-example.gif)

## Install
Install python 3 and install i3ipc libary

`pip3 install i3ipc`

Clone this repo and copy the scripts in any folder you like.

Example
```
git clone https://github.com/Hippo0o/i3-master-layout
cd i3-master-layout
cp i3-master-layout.py i3-swap-master.py i3-swallow-stack.py ~/.i3
```

## Usage
```
bindsym $mod+r exec --no-startup-id $HOME/.i3/i3-swap-master.py

exec_always --no-startup-id $HOME/.i3/i3-master-layout.py
```
## Options
```
$ ./i3-master-layout.py -h
Usage: i3-master-layout.py [options]

Options:
  -h, --help            show this help message and exit
  -e ws1,ws2,.. , --exclude-workspaces=ws1,ws2,.. 
                        List of workspaces that should be ignored.
  -o HDMI-0,DP-0,.. , --outputs=HDMI-0,DP-0,.. 
                        List of outputs that should be used instead of all.
  -n, --nested          Also move new windows which are created in nested
                        containers.
  --disable-rearrange   Disable the rearrangement of windows when the master
                        window disappears.
```

## TODO
- ~~fix stack behaviour when master window is closed~~
- make stack layout configurable (stacked, tabbed, splith, splitv)
- maybe a focused based master selection (focused will get master automatically)
---
## Swallow
Additionally there is a simple script [i3-swallow-stack.py](./i3-swallow-stack.py) which enables a simple swallow mechanism by utilizing the stack/tabbed layout default to i3.

### Options
```
$ ./i3-swallow-stack.py -h
usage: i3-swallow-stack.py [-h] [-d] [-t] cmd [cmd ...]

i3-swallow-stack

positional arguments:
  cmd         Command to be executed

options:
  -h, --help  show this help message and exit
  -d          Don't move window back to original parent on exit.
  -t          Use i3's tabbed layout instead of stack.
```
*Tip: if a cmd needs to use the same flags run it like this `./i3-swallow-stack.py [-d] [-t] -- cmd [-d] [-t]`*

Example
```bash
./i3-swallow-stack.py feh ...
```
![swallow](./i3-swallow-stack-example.gif)
