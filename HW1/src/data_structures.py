from typing import Dict, List, Optional
from collections.abc import MutableSequence
from collections import deque, UserDict
import copy


#A lot of classes are to modelize the different data being passed through the pipelines. Access methods can be numerous and not so elegant to read, 
#but rest assured they're only hear for convenience of code elsewhere

class Instruction():
    def __init__(self, pc, opcode, dest_reg, src_reg1, src_reg2, imm):
        self.opcode: Optional[str] = opcode
        self.rd: int = dest_reg
        self.rs1: Optional[int] = src_reg1
        self.rs2: Optional[int] = src_reg2
        if imm is not None:
            if int(imm)<0:
                imm += (1<<64)
        self.imm: Optional[int] = int(imm) if imm is not None else None
        self.pc = pc

    def __lt__(self, other):
        return self.pc < other.pc


class ALUEntry():
    def __init__(self, pc, opcode, dest_reg, val1, val2):
        self.pc = pc
        self.dest_reg = dest_reg
        self.opcode = opcode
        self.val1 = val1
        self.val2 = val2

    def __repr__(self):
        return f"ALU Entry: PC: {self.pc}, RD: {self.dest_reg}, opcode: {self.opcode}"

class ALU():
    def __init__(self):
        self.instructions = deque([], maxlen=3)

    def can_enqueue(self):
        return len(self.instructions)


    def enqueue(self, ins):
        if len(self.instructions) == 0:
            self.instructions = deque([None], maxlen=3)
        self.instructions.appendleft(ins)

    def run(self, ds):
        completed = None
        error = False
        try:
            completed = self.instructions.pop()
        #ALU is not being used right now
        except:
            pass

        #Empty instruction, either placeholder or ALU not used
        if completed is None:
            pass
        else:
            result = 0
            opcode = completed.opcode
            #Case switch like but too lazy to risk conflicts w/ python 3.10
            if opcode == "add" : 
                result = completed.val1 + completed.val2
            elif opcode == "sub":
                result = (completed.val1 - completed.val2) % (1<<64)
            elif opcode == "mulu":
                #Force to fall back to 64-bit
                result = ((completed.val1 * completed.val2) % (1<<64))
            elif opcode == "divu":
                if completed.val2 == 0:
                    error = True
                else:
                    result = completed.val1 / completed.val2
            elif opcode == "remu":
                if completed.val2 == 0:
                    error = True
                else:
                    result = completed.val1 % completed.val2

            ds.forwarding_paths.append(ForwardingPathsEntry(completed.pc, completed.dest_reg, result, error))


class ALUs():
    def __init__(self):
        self.alus = [copy.deepcopy(ALU()), copy.deepcopy(ALU()), copy.deepcopy(ALU()), copy.deepcopy(ALU())]

    def enqueue(self, ins):
        target_alu = self.alus[0]
        target_min = target_alu.can_enqueue()
        for alu in self.alus:
            if alu.can_enqueue()<target_min:
                target_alu = alu
                target_min = target_alu.can_enqueue()
        target_alu.enqueue(ins)
        return

    def run(self, ds):
        for alu in self.alus:
            alu.run(ds)

    def exception_wipe(self):
        self.alus = [copy.deepcopy(ALU()), copy.deepcopy(ALU()), copy.deepcopy(ALU()), copy.deepcopy(ALU())]


class DecodedInstructionRegister():
    def __init__(self):
        self.buffer = list()
        self.pcs = list()
        self.backpressure = False

    def fill(self, instructions):
        self.buffer = self.buffer + instructions.copy()
        #Sort by lowest PC
        self.buffer.sort()
        self.pcs = [ins.pc for ins in self.buffer]

    def apply_backpressure(self):
        self.backpressure = True

    def remove_backpressure(self):
        self.backpressure = False

    def isEmpty(self):
        return len(self.buffer) == 0

    def dump(self):
        return {"DecodedPCs" : self.pcs}

    

class FreeList():
    def __init__(self):
        self.free : List = list(range(32, 64))

    def pop(self, i):
        return self.free.pop(i)

    def append(self, item):
        self.free.append(item)

    def dump(self):
        return {"FreeList": self.free}

    def __len__(self):
        return len(self.free)



class RegisterMapTable(MutableSequence):
    def __init__(self):
        #All physical registers map to themselves on init
        self.mapping : List = list(range(0, 32))
        super().__init__()

    def __getitem__(self, i):
        return self.mapping[i]

    def __setitem__(self, i, item):
        self.mapping[i] = item

    def __delitem__(self, i):
        del self.mapping[i]

    def __len__(self):
        return len(self.mapping)

    def insert(self, i, item):
        self.mapping.insert(i, item)

    def dump(self):
        return {"RegisterMapTable" : self.mapping}



class BusyBitTable():
    def __init__(self):
        self.table : List = [False]*64

    def __getitem__(self, i):
        return self.table[i]

    def __setitem__(self, i, item):
        self.table[i] = item

    def __delitem__(self, i):
        del self.table[i]

    def __len__(self):
        return len(self.table)

    def insert(self, i, item):
        self.table.insert(i, item)

    def dump(self):
        return {"BusyBitTable" : self.table}




class ActiveListEntry():
    def __init__(self, log_dest, old_dest, pc, phys):
        self.done = False
        self.exception = False
        self.log_dest = log_dest
        self.old_dest = old_dest
        self.pc = pc
        self.phys_dest = phys

    def dump(self):
        return {"Done": self.done,
                "Exception": self.exception,
                "LogicalDestination": self.log_dest,
                "OldDestination": self.old_dest,
                "PC": self.pc}



class ActiveList():
    def __init__(self):
        self.table : List = []
        self.ordered_by_pc = dict()

    def __getitem__(self, i):
        return self.table[i]

    def __delitem__(self, pc):
        del self.ordered_by_pc[pc]
        self.table = list(self.ordered_by_pc.values())


    def append(self, item):
        self.table.append(item)
        self.ordered_by_pc = dict(map(lambda x: (x.pc, x), self.table))

    def remove(self, pc):
        target = self.ordered_by_pc[pc]
        del self.ordered_by_pc[pc]
        self.table.remove(target)
                

    def find_by_pc(self, pc):
        return self.ordered_by_pc[pc]

    def dump(self):
        return {"ActiveList": [entry.dump() for entry in self.table]}

    def __len__(self):
        return len(self.table)

    def isEmpty(self):
        return len(self.table) == 0

    



class PhysicalRegisterFile(MutableSequence):
    def __init__(self):
        self.table :List = [0]*64
        super().__init__()

    def write(self, reg, value):
        self.table[reg] = value

    def read(self, reg):
        return self.table[reg]

    def __getitem__(self, i):
        return self.table[i]

    def __setitem__(self, i, item):
        self.table[i] = item

    def __delitem__(self, i):
        del self.table[i]

    def __len__(self):
        return len(self.table)

    def insert(self, i, item):
        self.table.insert(i, item)

    def dump(self):
        return {"PhysicalRegisterFile": self.table}

    




class IntegerQueueEntry():
    def __init__(self, ins : Instruction , opAr, opBr, opAregTag = 0, opAval = 0, opBregTag = 0, opBval =0):
        self.dest_reg = ins.rd
        self.OpAIsReady = opAr
        self.OpAregTag = 0 if opAr else opAregTag
        self.OpAValue = 0 if not opAr else opAval
        self.OpBIsReady = opBr
        self.OpBregTag = 0 if opBr else opBregTag
        self.OpBValue = 0 if not opBr else opBval
        self.OpCode = ins.opcode
        self.pc = ins.pc

    def dump(self):
        return {"DestRegister": self.dest_reg, 
                "OpAIsReady"  : self.OpAIsReady,
                "OpARegTag"   : self.OpAregTag,
                "OpAValue"    : self.OpAValue,
                "OpBIsReady"  : self.OpBIsReady,
                "OpBRegTag"   : self.OpBregTag,
                "OpBValue"    : self.OpBValue,
                "OpCode"      : self.OpCode,
                "PC"          : self.pc
                }

    def __lt__(self, other):
        return self.pc < other.pc



class IntegerQueue():
    def __init__(self):
        self.table  = []
        self.ordered_by_pc = dict()

    def dump(self):
        self.table.sort()
        return {"IntegerQueue" : [entry.dump() for entry in self.table]}

    def append(self, item):
        self.table.append(item)
        self.ordered_by_pc = dict(map(lambda x: (x.pc, x), self.table))

    def find_by_pc(self, pc):
        return self.ordered_by_pc[pc]

    def check_forwarding_path(self, fwd):
        for reg, val in fwd.get_all_regs().items():
            if not val.exception:
                for e in self.table:
                        if e.OpAregTag == reg:
                            e.OpAIsReady = True
                            e.OpAValue = val.value
                            e.OpAregTag = 0
                        if e.OpBregTag == reg:
                            e.OpBIsReady = True
                            e.OpBValue = val.value
                            e.OpBregTag = 0
            #Empty the forwarding paths after the issue stage
        return


    def __getitem__(self, i):
        return self.table[i]
    
    def __setitem__(self, pc,  x):
        self.ordered_by_pc[pc] = x
        self.table = list(self.ordered_by_pc.values())

    def __delitem__(self, pc):
        del self.ordered_by_pc[pc]
        self.table = list(self.ordered_by_pc.values())

    def __len__(self):
        return len(self.table)


class ForwardingPathsEntry():
    def __init__(self, pc, reg, value, exception):
        self.pc = pc
        self.reg = reg
        self.value = value
        self.exception = exception

class ForwardingPaths():
    def __init__(self):
        self.reg_table = dict()
        self.pc_table = dict()

    def __setitem__(self, key, value):
        self.forwarding_paths[key] = value

    def append(self, res):
        self.reg_table[res.reg] = res
        self.pc_table[res.pc] = res


    def get_by_pc(self, pc):
        return self.pc_table[res.pc]

    def get_by_reg(self, reg):
        return self.reg_table[res.reg]


    def get_all_pcs(self):
        return copy.deepcopy(self.pc_table)
    
    def get_all_regs(self):
        return copy.deepcopy(self.reg_table)

    def del_by_pc(self, pc):
        target = self.pc_table[pc]
        del self.pc_table[pc]
        del self.reg_table[target.reg]

    def del_by_reg(self, reg):
        target = self.reg_table[reg]
        del self.reg_table[reg]
        del self.pc_table[target.pc]

    def __repr__(self):
        return f"\tForwarding paths: {[(a.reg, a.value) for a in self.pc_table.values()]}"

    
class DataStructures():
    def __init__(self):
        self.forwarding_paths = ForwardingPaths()
        self.dir = DecodedInstructionRegister()
        self.free_list = FreeList()
        self.active_list = ActiveList()
        self.integer_queue = IntegerQueue()
        self.busy_bit_table = BusyBitTable()
        self.register_map_table = RegisterMapTable()
        self.physical_register_file = PhysicalRegisterFile()
        self.program_counter = 0
        self.exception_flag = False
        self.exception_pc = 0
        self.ALUs = ALUs()
        self.cycle = 0

    def dumpState(self):
        components = [self.dir,
                      self.free_list, 
                      self.active_list, 
                      self.integer_queue, 
                      self.busy_bit_table, 
                      self.register_map_table, 
                      self.physical_register_file]
        a = dict()
        for c in components:
            a |= copy.deepcopy(c.dump())
        a |= {"Exception" : self.exception_flag, 
              "ExceptionPC":self.exception_pc,
              "PC": self.program_counter}

        return dict(sorted(a.items()))

    def __repr__(self):
        return self.dir.__repr__()


