from managers.WorkspaceLayoutManager import WorkspaceLayoutManager
import utils

class MasterStackLayoutManager(WorkspaceLayoutManager):

    def __init__(self, con, workspaceId, options):
        self.con = con
        self.workspaceId = workspaceId
        self.masterId = 0
        self.stackIds = []
        self.debug = options.debug
        self.masterWidth = options.masterWidth
        self.stackLayout = options.stackLayout


    def setMasterWidth(self):
        self.con.command('[con_id=%s] resize set %s 0 ppt' % (self.masterId, self.masterWidth))


    def moveWindow(self, subject, target):
        self.con.command("[con_id=%d] mark --add move_target" % target)
        self.con.command("[con_id=%d] move container to mark move_target" % subject)
        self.con.command("[con_id=%d] unmark move_target" % target)


    def pushWindow(self, subject):
        # Only record window if stack is empty
        if self.stackIds == []:
            # Check if master is empty too
            if self.masterId == 0:
                self.masterId = subject
            else:
                self.stackIds.append(subject)
                self.setMasterWidth()
            return

        # Check if we're missing master but have a stack, for some reason
        if self.masterId == 0:
            self.masterId = subject
            return

        # Put new window at top of stack
        target = self.stackIds[-1]
        self.moveWindow(subject, target)
        self.con.command("[con_id=%s] focus" % subject)
        self.con.command("move up")

        # Swap with master
        oldMaster = self.masterId
        self.con.command("[con_id=%d] swap container with con_id %d" % (subject, oldMaster))
        self.setMasterWidth()

        # Update record
        self.stackIds.append(self.masterId)
        self.masterId = subject


    def popWindow(self):
        # Check if last window is being popped
        if self.stackIds == []:
            self.masterId = 0
            return

        # Move top of stack to master position
        self.masterId = self.stackIds.pop()
        self.con.command("[con_id=%s] focus" % self.masterId)
        self.con.command("move left")
        self.setMasterWidth()


    def rotateUp(self):
        # Exit if less than three windows
        if len(self.stackIds) < 2:
            return

        newMaster = self.stackIds.pop()
        oldMaster = self.masterId
        bottom = self.stackIds[0]

        # Swap top of stack with master, then move old master to bottom
        self.log("New window id: %d" % newWindow.id)
        self.con.command("[con_id=%d] swap container with con_id %d" % (newMaster, oldMaster))
        self.moveWindow(oldMaster, bottom)

        # Update record
        self.masterId = newMaster
        self.stackIds.insert(0, oldMaster)


    def swap_master(self):
        # Exit if less than two windows
        if self.stack_ids == []:
            return
            
        focused_window = utils.findFocused(self.con)

        if focused_window is None:
            return
        
        if focused_window.id == self.master_id:
            return

        # Find focused window in record
        for i in range(len(self.stack_ids)):
            if self.stack_ids[i] == focused_window.id:
                # Swap window with master
                self.con.command("[con_id=%d] swap container with con_id %d" % (focused_window.id, self.master_id))
                self.stack_ids[i] = self.master_id
                self.master_id = focused_window.id
                return


    def windowCreated(self, event):
        newWindow = utils.findFocused(self.con)
        
        # New window replcases master, master gets pushed to stack
        self.log("New window id: %d" % newWindow.id)
        self.pushWindow(newWindow.id)


    def windowFocused(self, event):
        # splith is not supported yet. idk how to differentiate between splith and nested splith.
        if self.stackIds != []:
            layout = self.stackLayout or "splitv"
            bottom = self.stackIds[0]
            self.con.command("[con_id=%d] split vertical" % bottom)
            self.con.command("[con_id=%d] layout %s" % (bottom, layout))
        else:
            self.con.command("[con_id=%d] split horizontal" % self.masterId)


    def windowClosed(self, event):
        self.log("Closed window id: %d" % event.container.id)
        # Try to remove window from stack, catch if its on a different workspace
        try:
            self.stackIds.remove(e.container.id)
            return
        except BaseException as e:
            return


    def binding(self, command):
        if command == "nop rotate up":
            self.rotateUp()
        elif command == "nop swap master":
            self.swapMaster()
