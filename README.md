# [WIP] swlm - Sway Workspace Layout Manager

swlm is a daemon that handles layout management on a per-workspace basis. Each `WorkspaceLayoutManager` (WLM) is
responsible for managing all of the tiling windows on a given workspace. The `mananagers/` directoy contains files
that each hold an implementation of a WLM, with `WorkspaceLayoutManager.py` containing the parent class from which
all WLMs are derived.

#### Currently implemented layouts

- Autotiling (based on nwg-piotr's [autotiling](https://github.com/nwg-piotr/autotiling/blob/master/autotiling/main.py))
- Master/Stack (My implementation, may not align with dwm/river)

#### TODO

- [ ] Differentiate WLMs that support managing existing windows
- [ ] Add warning when enabling WLMs that don't support existing windows on a workspace with windows
- [ ] More Layouts!
