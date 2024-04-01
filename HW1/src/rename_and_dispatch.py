from typing import Optional
from data_structures import *

class RenameAndDispatchUnit():
    def __init__(self, data_structures : DataStructures):
        # self.renamer = Renamer()
        # self.dispatcher = Dispatcher()
        self.ds = data_structures
        self.to_update = True
        self.seen_to_rename = list()
    
    
    def _check_for_space(self, size):
        pred = len(self.ds.free_list) >= size 
        pred = pred and len(self.ds.active_list) <= (32-size) 
        pred = pred and len(self.ds.integer_queue) <= (32-size)
        return pred

    def update_with_fwd(self):
        for reg, entry in self.ds.forwarding_paths.get_all_regs().items():
            if not entry.exception:
                self.ds.physical_register_file[reg] = entry.value
                self.ds.busy_bit_table[reg] = False
            self.ds.forwarding_paths.del_by_reg(reg)


    #We are forced to execute the entire phase suite of operations for each instruction
    #Otherwise we risk overwriting the physical register map entry and it'll mess up our Tag entry
    #
    def rename_and_dispatch(self):
        ds = self.ds
        DIR = ds.dir
        size = min(4, len(DIR.buffer))
        if not self._check_for_space(size):
            self.ds.dir.backpressure = True
            return
        to_rename = []
        renamed = []
        #Retrieve instructions from the DIR
        if len(DIR.buffer)<4:
            to_rename = DIR.buffer
            ds.dir.buffer = []
        else:
            to_rename = DIR.buffer[0:4]
            ds.dir.buffer = DIR.buffer[4:]

        for ins in to_rename:
            phys_reg = ds.free_list.pop(0)
            old_dest = ds.register_map_table[ins.rd]
            physRegA = ds.register_map_table[ins.rs1]
            if ins.imm is None:
                physRegB = ds.register_map_table[ins.rs2]

            ds.register_map_table[ins.rd] = phys_reg
            logical_dest = ins.rd
            ins.rd = phys_reg

            opAr = True
            opAVal = 0 
            #If waiting on Execution stage
            if ds.busy_bit_table[physRegA]:
                opAr = False

            opAVal = ds.physical_register_file[physRegA]
            opARegTag = physRegA if not opAr else 0
            
            opBr = True
            opBVal = 0 
            if ins.imm is not None:
                opBr = True
                opBVal = ins.imm
                opBRegTag = 0
            else:
                if ds.busy_bit_table[physRegB]:
                    opBr = False

                opBRegTag = physRegB if not opBr else 0
                opBVal = ds.physical_register_file[physRegB]


            iqe = IntegerQueueEntry(ins, opAr, opBr, opARegTag, opAVal, opBRegTag, opBVal)

            self.ds.busy_bit_table[phys_reg] = True
            self.ds.integer_queue.append(iqe)
            ace = ActiveListEntry(logical_dest, old_dest, ins.pc, ins.rd) 
            self.ds.active_list.append(ace)


    def run(self):
            if self.ds.exception_flag:
                return
            self.update_with_fwd()
            self.rename_and_dispatch()
