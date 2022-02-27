# [WIP] swlm - Sway Workspace Layout Manager

swlm is a daemon that handles layout management on a per-workspace basis. Each WorkspaceLayoutManager [WLM] is responsible for managing all of the tiling windows on a given workspace. The mananagers directoy contains files that each hold an implementation of WorkspaceLayoutManager, with `WorkspaceLayoutManager.py` containing the parent class from which all WLMs are derived.
