from data_structures import *



class CommitUnit():
    def __init__(self, data_structures):
        self.ds = data_structures
        self.exception_pc = 0
        self.will_except = False


    def run(self):
        if len(self.ds.active_list) == 0:
            self.ds.exception_flag = False

        if self.ds.exception_flag:
            to_rollback = self.ds.active_list.table[-4:]
            for ale in to_rollback[::-1]:
                phys_reg = self.ds.register_map_table[ale.log_dest]
                self.ds.busy_bit_table[phys_reg] = False
                self.ds.free_list.append(phys_reg)
                self.ds.register_map_table[ale.log_dest] = ale.old_dest
                self.ds.active_list.remove(ale.pc)
            return


        nb_committed = 0
        al = copy.deepcopy(self.ds.active_list)
        for e in al:
            if nb_committed >= 4:
                break
            if e.done:
                if not e.exception:
                    self.ds.free_list.append(e.old_dest)
                    del self.ds.active_list[e.pc]
                    nb_committed +=1
                else:
                    #Exception mode
                    self.ds.exception_flag = True
                    self.ds.exception_pc = e.pc
                    self.ds.integer_queue = IntegerQueue()
                    self.ds.ALUs.exception_wipe()
                    break
            else:
                break

        #Begin by marking all available forwarded instructions as done and potentially raising an exception

        for pc, entries in self.ds.forwarding_paths.get_all_pcs().items():
            t = self.ds.active_list.find_by_pc(pc)
            t.done = True
            t.exception = entries.exception
