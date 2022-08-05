# swlm - Sway Workspace Layout Manager

swlm is a daemon that handles layout management on a per-workspace basis. Each `WorkspaceLayoutManager` (WLM) is
responsible for managing all of the tiling windows on a given workspace. The `mananagers/` directoy contains files
that each hold an implementation of a WLM, with `WorkspaceLayoutManager.py` containing the parent class from which
all WLMs are derived.

The main goal of swlm is to simplify sway(i3)-ipc into a framework/interface for programatically managing windows per-workspace.

```
Usage: swlm.py [options]

Options:
  -h, --help                   show this help message and exit
  -c .config/swlm/config.toml, --config=.config/swlm/config.toml
                               Path to user config file.
```

### TODO
- [ ] Improve configuration
  - [ ] Load custom WorkspaceLayoutManagers from config path
  - [ ] Reload config without restarting swlm
- [ ] More Layouts!
- [ ] MasterStack:
  - [ ] Maintain user-set window sizes for each wndow position
  - [ ] Automatically arrange pre-existing windows into correct layout
  - [ ] Fix rotation

## Installation

Because swlm is still early in development, I haven't come up with a way to package it yet. For now, clone this
repositiory and symlink `swlm.py` to `~/.local/bin/swlm` or any directoy in your PATH.

## Configuration

swlm is configured using the config file at `$HOME/.config/swlm/config.toml` using TOML. The `[swlm]` table configures
options specific to the main swlm daemon, and any that should apply to all outputs and workspaces. Specific outputs and
workspaces can be configured in their own sections by using `[output.VALUE]` or `[workspace.VALUE]` header, where `VALUE`
is either the name of the output, or the number of the workspace being configured. Any options configured will override
the values set in the `[swlm]` section for that output or workspace. Note, values configured for outputs will only apply
to workspaces **created** on that output. For an example configuration, see the config.toml file in the root of this repo.

## Layout Managers

The layout manager controlling a workspace can be dynamically changed using the command `nop swlm layout <LAYOUT>`. In
order to handle window movement in layouts that don't use standard sway up/down/left/right, a WLM can override
these commands with better defaults, and swlm will fall back the regular command for WLMs that don't. To use the
WLM provided movement commands, replace your `move <direction>` bindsyms with
```
# Override move binds
bindsym $mod+Shift+Left nop swlm move left
bindsym $mod+Shift+Down nop swlm move down
bindsym $mod+Shift+Up nop swlm move up
bindsym $mod+Shift+Right nop swlm move right
```

### none

The `none` layout manager does not manage any windows. It exists as a reference implementation, and to allow users
to disable layout management on a given workspace.

Config options:
```
debug: Boolean to control debug messages
```

Binding:
```
bindym <your bind here> nop swlm layout none # disable layout management on a workspace
```

### Autotiling

Based on nwg-piotr's [autotiling](https://github.com/nwg-piotr/autotiling/blob/master/autotiling/main.py),
the `Autotiling` layout manager alternates between splith and splitv based on a windows height/width ratio.
`Autotiling` excludes floating tabbed, and stacked windows.

Config options:
```
debug: Boolean to control debug messages
```

Binding:
```
bindym <your bind here> nop swlm layout Autotiling # set focused workspace's layout manager to Autotiling
```

### MasterStack

`MasterStack` is inspired by dwm/dwl/river, but is my own take on it. It implements a master window with a stack
on the right side. When a new window is created, it replaces master and master is placed on top of the stack.
If the master window is deleted, the top of the stack replaces master. The layout of the stack container can be
`splitv`, `tabbed`, or `stacking` The layout of the stack can be toggled using a keybind.

`MasterStack` also implements a keybind for swapping. When swapping, the focused window is swapped with master. If
the focused window is master, it gets swapped with the top of the stack. `MasterStack` also implements rotation.
When rotating counter-clockwise, master is moved to the bottom of the stack, and the top of the stack becomes the
new master. Conversely, rotating clockwise moves master to the top of the stack, and the bottom of the stack
becomes the new master.

`MasterStack` provides overrides for `move <directon>` binds. 

Known bugs:
-  Rotation got broked
-  Sometimes existing windows get missed when arranging an existing layout

Config options:
```
debug: Boolean to control debug messages
masterWidth: Int to control the percent width of master window [1-99]
stackLayout: String to control the layout of the stack ["splitv", "tabbed", "stacking"]
```

Bindings:
```
bindym <your bind here> nop swlm layout MasterStack # set focused workspace's layout manager to MasterStack
bindym <your bind here> nop swlm swap master # swap focused window with master
bindym <your bind here> nop swlm rotate cw # rotate layout cw 1 window
bindym <your bind here> nop swlm rotate ccw # rotate layout ccw 1 window
bindym <your bind here> nop swlm move up # move focused winodw up 1 position in the stack
bindym <your bind here> nop swlm move down # move focused window down one position in the stack
bindym <your bind here> nop swlm stack toggle # toggles stack layout through splitv, tabbed, and stacking
```
