class WorkspaceLayoutManager:
    def __init__(self, con, workspaceId):
        self.con = con
        self.workspaceId = workspaceId
        self.debug = options.debug


    def log(self, msg):
        if self.debug:
            print(("workspace %d: " % self.workspaceId) + msg)

    def windowCreated(self, event):
        pass


    def windowFocused(self, event):
        pass


    def windowClosed(self, event):
        pass

    def binding(self, command):
        pass
