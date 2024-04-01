from data_structures import *
import copy


class IssueUnit():
    def __init__(self, data_structures):
        self.ds = data_structures


    def run(self):
        if self.ds.exception_flag:
            return

        iq = copy.deepcopy(self.ds.integer_queue)
        iq.check_forwarding_path(self.ds.forwarding_paths)
        nb_issued = 0
        for i in range(len(iq)):
            issued = False
            entry = iq[i]
            if entry.OpAIsReady and entry.OpBIsReady:
                if nb_issued < 4:
                    issued = True
                    del self.ds.integer_queue[entry.pc]
                    #Enqueue into the ALUs
                    self.ds.ALUs.enqueue(ALUEntry(entry.pc, entry.OpCode, entry.dest_reg, entry.OpAValue, entry.OpBValue))
                    nb_issued += 1
            if not issued:
                self.ds.integer_queue[entry.pc] = entry

class ExecuteUnit():
    def __init__(self, data_structures):
        self.ds = data_structures


    def run(self):
        self.ds.ALUs.run(self.ds)
