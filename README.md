# layman

layman is a daemon that handles layout management on a per-workspace basis. Each `WorkspaceLayoutManager` (WLM) is
responsible for managing all of the tiling windows on a given workspace. 

WLMs are intended to have a simpler set of events than those provided though i3ipc-python, since the scope is limited
to a single workspace. See the User Created Layouts section for how to add a new layout.

```
Usage: layman.py [options]

Options:
  -h, --help                   show this help message and exit
  -c .config/layman/config.toml, --config=.config/layman/config.toml
                               Path to user config file.
```

## Installation

I intend to provide installation through PyPi using pip, however the original name of this project `swlm` was forbidden for
being too similar to another package, swmm. After rebranding to `layman`, the name is still forbidden for an unkown reason.
Until this is resolved, please use the instructions below.

For Arch users, `layman-git` is available [on the AUR](https://aur.archlinux.org/packages/layman-git) courtesy of [matclab](https://github.com/matclab)

## Installing from source
```
git clone https://github.com/frap129/layman
pip install ~/path/to/layman
```
to package and install layman. If you do not want to have to reinstall after a change, add --editable to the pip command

## Configuration

layman is configured using the config file at `$HOME/.config/layman/config.toml`. The `[layman]` table configures
options for layman, and defaults options for WLMs. Specific outputs and workspaces can be configured using
`[output.VALUE]` or `[workspace.VALUE]` header, where `VALUE` is the name of the output or the workspace number.
Any options configured will override the values set in the `[layman]` table for that output or workspace. For an example
configuration, see the `config.toml` file in the root of this repo.

Note, values configured for outputs will only apply to workspaces **created** on that output.

The config can be reloaded at runtime with `layman reload`. Note that this reloads the config, but
not the layout managers. Config changes for existing layouts won't take affect until the managers is reset with
`layman layout <layout short name>`.

## Usage

To start using layman, simply run `layman`. This is best done in your sway/i3 config, or a setup script.

To send commands to layman, you can either bind `nop layman <command>` to a key, or execute `layman` again with arguments.
You could bind `exec layman <command>` to a key, but using `nop` is prefered to avoid overhead.

Commands:
```
move <up|down|left|right> # Passes movement to a WLM to hanldle, or back to sway/i3
reload # Reloads config and user layouts
layout <layout shortname> # Sets a new layout on the focused workspace
```

Layouts may add their own commands, refer to the layouts below for more commands.

## Layout Managers

The layout manager controlling a workspace can be changed using the command `nop layman layout <LAYOUT>`. In order to
handle window movement in layouts that don't use standard up/down/left/right, a WLM can override these commands with better
defaults, and layman will fall back the regular command for WLMs that don't. To use the WLM provided movement commands,
replace your `move <direction>` bindsyms with
```
# Override move binds
bindsym $mod+Shift+Left nop layman move left
bindsym $mod+Shift+Down nop layman move down
bindsym $mod+Shift+Up nop layman move up
bindsym $mod+Shift+Right nop layman move right
```

The `src/mananagers/` directoy contains files that each hold an implementation of a WLM, with `WorkspaceLayoutManager.py`
containing the parent class from which all WLMs are derived.

### none

The `none` layout manager does not manage any windows. It exists as a reference implementation, and to allow users
to disable layout management on a given workspace.

Commands:
```
layman layout none # disable layout management on a workspace
```

### Autotiling

Based on nwg-piotr's [autotiling](https://github.com/nwg-piotr/autotiling/blob/master/autotiling/main.py),
the `Autotiling` layout manager alternates between splith and splitv based on a windows height/width ratio.

Config options:
```
depthLimit: Max number of nested splits [0 means no limit]
```

Commands:
```
layman layout Autotiling # set focused workspace's layout manager to Autotiling
```

### Grid

![](docs/Grid.gif)

Like autotiling, Grid splits window based on width/height ratio. It differs from Autotiling by always splttting
the largest existing window, rather than the currently focused window. If multiple windows have the same size,
Grid tries to split the left-most and top-most "largest" window. This results in a grid-like pattern.

Commands:
```
layman layout Grid # set focused workspace's layout manager to Grid
```
### MasterStack

![](docs/MasterStack.gif)

`MasterStack` is inspired by dwm/dwl/river, but is my own take on it. It implements a master window with a stack
on the side. When a new window is created, it replaces master and master is placed on top of the stack.
If the master window is deleted, the top of the stack replaces master. The layout of the stack container can be
`splitv`, `tabbed`, or `stacking`. The layout of the stack can be toggled using a keybind.

`MasterStack` also implements a keybind for swapping. When swapping, the focused window is swapped with master. If
the focused window is master, it gets swapped with the top of the stack. `MasterStack` also implements rotation.
When rotating left, master is moved to the bottom of the stack, and the top of the stack becomes master.
Rotating right moves master to the top of the stack, and the bottom of the stack becomes master.

`MasterStack` provides overrides for `move <directon>` binds. 

Known bugs:
-  Sometimes existing windows get missed when arranging an existing layout

Config options:
```
masterWidth: Int to control the percent width of master window [1-99]
stackLayout: String to control the layout of the stack ["splitv", "tabbed", "stacking"]
stackSide: String to control which side of the screen the stack is on ["right", "left"]
```

Commands:
```
layman layout MasterStack # set focused workspace's layout manager to MasterStack
layman swap master # swap focused window with master
layman rotate cw # rotate layout cw 1 window
layman rotate ccw # rotate layout ccw 1 window
layman move up # move focused winodw up 1 position in the stack
layman move down # move focused window down one position in the stack
layman stack toggle # toggles stack layout through splitv, tabbed, and stacking
layman stackside toggle # toggles stack side between left and right
```

### User Created Layouts

You can create layouts that get picked up and managed by layman without modifying layman itself. Any python file placed
in the same directory as the config file will be automatically imported by layman at startup, and any time the
configuration is reloaded. To get started writing your own layouts, take a look at `src/mangers/WorkspaceLayoutManger.py`
in this repo. This is the base class from which your layout must inherit, and provides a number of hooks and functions
for handling window events. `src/managers/AutotilingLayoutManager.py` is a simple example of how to implement a WLM.
When making a WLM, make sure that it has a unique shortname.
