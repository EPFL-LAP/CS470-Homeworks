#!/usr/bin/env python3

import json
import argparse

parser = argparse.ArgumentParser()
parser.add_argument(
    "instructions", type=argparse.FileType("r"), 
    help="The JSON file defining the instruction to be executed"
)
parser.add_argument(
    "result", type=argparse.FileType("w"),
    help="The cycle-accurate simulation result."
)
parser.add_argument(
    "--memory", type=argparse.FileType("r"),
    help="Optional data memory JSON initialization file."
)

arg = parser.parse_args()

instructionMemory: list[list[str]] = json.load(arg.instructions)

class DataMemory:
    data = {}

    def __init__(self, initFile: dict):
        for addr, data in initFile.items():
            if addr.startswith("0x"):
                self.data[int(addr, 16)] = data
            else:
                self.data[int(addr)] = data
    
    def read(self, addr: int) -> int:
        if self.data.get(addr) is None:
            return 0
        else:
            return self.data.get(addr)

    def write(self, addr: int, data: int) -> int:
        self.data[addr] = data

if arg.memory:
    dataMemory = DataMemory(json.load(arg.memory))
else:
    dataMemory = DataMemory({})

state = []


class VLIW470:
    # Visible Architecture State.
    PC = 0
    _PC = 0
    RBB = 0
    _RBB = 0
    LC = 0
    _LC = 0
    EC = 0
    _EC = 0
    PhysicalRegisterFile = [0 for _ in range(96)]
    _PhysicalRegisterFile = []
    PredicateRegisters = [False for _ in range(96)]
    _PredicateRegisters = []

    # Functional pipelines
    ALU0Pipe = {
        "predicate": False,
        "opcode": "alu", # alu, updateLC, updateEC, updateRBB, updatePredicate
        "targetReg": 0,
        "value": 0
    }

    ALU1Pipe = {
        "predicate": False,
        "opcode": "",
        "targetReg": 0,
        "value": 0
    }

    BranchPipe = {
        "predicate": False,
        "opcode": "hw", # lw or loop
        "targetPC": 0,
    }

    MemoryPipe = {
        "predicate": False,
        "opcode": "load", # load or store
        "address": 0,
        "data": 0,
        "loadDestReg": 0,
    }

    MultiplierPipe = [
        {
            "predicate": False,
            "targetReg": 0,
            "result": 0,
        },
        {
            "predicate": False,
            "targetReg": 0,
            "result": 0,
        }
    ]

    def serialize(self) -> dict:
        return {
            "PC": self.PC,
            "RBB": self.RBB,
            "LC": self.LC,
            "EC": self.EC,
            "PhysicalRegisterFile": self.PhysicalRegisterFile.copy(),
            "PredicateRegisters": self.PredicateRegisters.copy(),
            "ALU0": self.ALU0Pipe.copy(),
            "ALU1": self.ALU1Pipe.copy(),
            "Branch": self.BranchPipe.copy(),
            "Memory": self.MemoryPipe.copy(),
            "Multiply": self.MultiplierPipe.copy(),
            "MemoryData": dataMemory.data.copy()
        }

    _debug_currentCycleUpdate = []

    def updateRegister(self, name: str, value: int):
        if name in self._debug_currentCycleUpdate:
            print("Warning: Multiple instructions are updating the register {}.".format(name))
        else:
            self._debug_currentCycleUpdate.append(name)
        
        if name.startswith("x"):
            self.PhysicalRegisterFile[int(name[1:])] = value
        elif name.startswith("p"):
            self.PredicateRegisters[int(name[1:])] = value != 0
        elif name == "LC":
            self.LC = value
        elif name == "RBB":
            self.RBB = value
        elif name == "EC":
            self.EC = value
        else:
            assert False, "Wrong register name is met: {}".format(name)

    def renameRegister(self, idx: int) -> int:

        assert idx >= 0 and idx < 96, "Trying to rename a register out of the specific range."

        if idx >= 32:
            potential = idx - self.RBB
            if potential < 32:
                return potential + 64
            return potential
        
        return idx

    def parseImmediate(self, i: str) -> int:
        if i.startswith("0x"):
            return int(i, 16) # at present we only support hex and decimal.
        return int(i)

    def parse(self, i: str) -> dict:
        # i could be a format like "(pX) inst dst, src, third"
        # this function is trying to separate the predication.
        info = i.split()
        predication = True
        info[0] = info[0].strip()
        if info[0].startswith("(") and info[0].endswith(")"):
            # with predication
            idx = int(info[0][2:-1].strip())
            assert idx <= 95, "Undefined predicate register: p{}".format(idx)
            predication = self.PredicateRegisters[self.renameRegister(idx)]
            info.remove(info[0])
        
        operands: list[str] = []

        for item in info[1:]:
            item = item.strip()
            if item.endswith(","):
                operands.append(item[:-1].strip())
            else:
                operands.append(item.strip())

        return {
            "predicate": predication,
            "opcode": info[0].strip(),
            "operands": operands
        }

    def decodeALUInstruction(self, i: str) -> dict:
        decoded = self.parse(i)
        predication: bool = decoded["predicate"]
        opcode: str = decoded["opcode"]
        ops: list[str] = decoded["operands"]
        
        # Now start the normal instruction decoding.
        assert opcode in ["add", "addi", "sub", "mov", "nop"], "Undefined instruction: {}".format(i)
        
        # classify instruction by its type
        if opcode in ["add", "addi", "sub"]:
            # define the source
            assert ops[0].startswith('x'), "Cannot determine the destination: {}".format(i)
            dest =  self.renameRegister(int(ops[0][1:]))

            assert ops[1].startswith('x'), "Cannot determine the source reg: {}".format(i)
            src1 = self.renameRegister(int(ops[1][1:]))

            if opcode == "addi":
                src2 = int(ops[2])
            else:
                assert ops[2].startswith('x'), "Cannot determine the 2nd source reg: {}".format(i)
                src2 = self.renameRegister(int(ops[2][1:]))

            result = 0
            if opcode == "add":
                result = self.PhysicalRegisterFile[src1] + self.PhysicalRegisterFile[src2]
            elif opcode == "addi":
                result = self.PhysicalRegisterFile[src1] + src2
            elif opcode == "sub":
                result = self.PhysicalRegisterFile[src1] - self.PhysicalRegisterFile[src2]
                if result < 0:
                    result = result + 0x10000000000000000 # 2-complementary
            result = result & 0xFFFFFFFFFFFFFFFF

            return {
                "predicate": predication,
                "opcode": "alu", # alu, updateLC, updateEC, updateRBB, updatePredicate
                "targetReg": dest,
                "value": result
            }

        elif opcode == "mov":
            if ops[0].startswith("p"):
                # it's updating a predicate
                idx = self.renameRegister(int(ops[0][1:]))

                if ops[1] == "true":
                    return {
                        "predicate": predication,
                        "opcode": "updatePredicate", # alu, updateLC, updateEC, updateRBB, updatePredicate
                        "targetReg": idx,
                        "value": 1
                    }
                elif ops[1] == "false":
                    return {
                        "predicate": predication,
                        "opcode": "updatePredicate", # alu, updateLC, updateEC, updateRBB, updatePredicate
                        "targetReg": idx,
                        "value": 0
                    }
                else:
                    assert False, "Cannot determine the source operand: {}".format(i)
            elif ops[0].upper() in ["LC", "EC", "RBB"]:
                dest = ops[0].upper()
                value = int(ops[1])
                if ops[0].upper() == "RBB":
                    assert value < 64, "The maximum value of RBB is 63. The value you provide causes overflow."
                return {
                    "predicate": predication,
                    "opcode": "update{}".format(dest), # alu, updateLC, updateEC, updateRBB, updatePredicate
                    "targetReg": 0,
                    "value": value
                }
            elif ops[0].startswith('x'):
                dst = self.renameRegister(int(ops[0][1:]))
                if ops[1].startswith('x'):
                    src = self.renameRegister(int(ops[1][1:]))
                    return {
                        "predicate": predication,
                        "opcode": "alu",
                        "targetReg": dst,
                        "value": self.PhysicalRegisterFile[src]
                    }
                else: # It should be an integer
                    return {
                        "predicate": predication,
                        "opcode": "alu",
                        "targetReg": dst,
                        "value": self.parseImmediate(ops[1])
                    }
            else:
                assert False, "Unknown instruction: {}".format(i)
        elif opcode == "nop":
            return {
                "predicate": False,
                "opcode": "alu", # alu, updateLC, updateEC, updateRBB, updatePredicate
                "targetReg": 0,
                "value": 0
            }

    def decodeMultiplierInstruction(self, i: str) -> dict:
        decoded = self.parse(i)
        predication: bool = decoded["predicate"]
        opcode: str = decoded["opcode"]
        ops: list[str] = decoded["operands"]

        assert opcode in ["mulu", "nop"]

        if opcode == "mulu":
            assert ops[0].startswith('x') and ops[1].startswith('x') and ops[2].startswith('x'), "Undefined instruction: {}".format(i)
            dest = self.renameRegister(int(ops[0][1:]))
            src1 = self.renameRegister(int(ops[1][1:]))
            src2 = self.renameRegister(int(ops[2][1:]))
            return {
                "predicate": predication,
                "targetReg": dest,
                "result": (self.PhysicalRegisterFile[src1] * self.PhysicalRegisterFile[src2]) & 0xFFFFFFFFFFFFFFFF,
            }
        else:
            return {
                "predicate": False,
                "targetReg": 0,
                "result": 0,
            }


    def decodeLoadStoreInstruction(self, i: str) -> dict:
        decoded = self.parse(i)
        predication: bool = decoded["predicate"]
        opcode: str = decoded["opcode"]
        ops: list[str] = decoded["operands"]

        assert opcode in ["ld", "st", "nop"]

        if opcode == "nop":
            return {
                "predicate": False,
                "opcode": "load", # load or store
                "address": 0,
                "data": 0,
                "loadDestReg": 0,
            }

        # ops[0]: xNN
        # ops[1]: imm(xMM)
        assert ops[0].startswith('x') and "(" in ops[1] and ")" in ops[1], "Undefined instruction: {}".format(i)

        dest = self.renameRegister(int(ops[0][1:]))
        imm = ops[1].split("(")[0].strip()
        if len(imm) == 0:
            imm = 0
        elif imm.startswith("0x"):
            imm = int(imm, 16)
        else:
            imm = int(imm)

        add = ops[1].split("(")[1].strip()[1:-1]
        addr = self.PhysicalRegisterFile[self.renameRegister(int(add))] + imm

        if opcode == "ld":
            return {
                "predicate": predication,
                "opcode": "load", # load or store
                "address": addr,
                "data": 0,
                "loadDestReg": dest,
            }
        elif opcode == "st":
            return {
                "predicate": predication,
                "opcode": "store", # load or store
                "address": addr,
                "data": self.PhysicalRegisterFile[dest],
                "loadDestReg": 0,
            }
            


    def decodeBrancInstruction(self, i: str) -> dict:
        decoded = self.parse(i)
        predication: bool = decoded["predicate"]
        opcode: str = decoded["opcode"]
        ops: list[str] = decoded["operands"]

        assert opcode in ["loop", "loop.pip", "nop"], "Undefined instruction: {}".format(i)

        if opcode == "loop":
            return {
                "predicate": predication,
                "opcode": "loop", # lw or loop
                "targetPC": int(ops[0]),
            }
        elif opcode == "loop.pip":
            return {
                "predicate": predication,
                "opcode": "hw", # lw or loop
                "targetPC": int(ops[0]),
            }

        return {
            "predicate": False,
            "opcode": "hw", # lw or loop
            "targetPC": 0,
        }

    def tick(self):
        ## PC Propagate
        if self.PC >= len(instructionMemory):
            inst = ["nop", "nop", "nop", "nop", "nop"]
        else:
            inst = instructionMemory[self.PC]
        
        assert len(inst) == 5, "Each bundle should always have 5 instructions"
    
        # Branch Unit will be immediately updated, because its' combinational logic.
        #### inst[0] -> ALU0
        self.ALU0Pipe = self.decodeALUInstruction(inst[0])
        #### inst[1] -> ALU1
        self.ALU1Pipe = self.decodeALUInstruction(inst[1])
        #### inst[2] -> MUL
        self.MultiplierPipe.insert(0, self.decodeMultiplierInstruction(inst[2]))
        #### inst[3] -> MEM
        self.MemoryPipe = self.decodeLoadStoreInstruction(inst[3])
        #### inst[4] -> Branch
        self.BranchPipe = self.decodeBrancInstruction(inst[4])

        # record the state
        state.append(self.serialize())

        # Now start latch other data structures.
        ## Execution Stage
        self._debug_currentCycleUpdate.clear()

        #### ALUs
        for aluPipe in [self.ALU0Pipe, self.ALU1Pipe]:
            if aluPipe["predicate"]:
                idx = aluPipe["targetReg"]
                value = aluPipe["value"]
                if aluPipe["opcode"] == "alu":
                    self.updateRegister("x{}".format(idx), value)
                elif aluPipe["opcode"] == "updateLC":
                    self.updateRegister("LC", value)
                elif aluPipe["opcode"] == "updateEC":
                    self.updateRegister("EC", value)
                elif aluPipe["opcode"] == "updateRBB":
                    self.updateRegister("RBB", value)
                elif aluPipe["opcode"] == "updatePredicate":
                    self.updateRegister("p{}".format(idx), value)
                else:
                    assert False, "Wrong opcode is provided: {}".format(aluPipe["opcode"])
        
        #### Memory
        if self.MemoryPipe["predicate"]:
            if self.MemoryPipe["opcode"] == "load":
                self.updateRegister(
                    "x{}".format(self.MemoryPipe["loadDestReg"]),
                    dataMemory.read(self.MemoryPipe["address"])
                )
            elif self.MemoryPipe["opcode"] == "store":
                dataMemory.write(
                    self.MemoryPipe["address"],
                    self.MemoryPipe["data"]
                )
            else:
                assert False, "Wrong opcode"

        #### Multiplier: the most complex one.
        ##### Always pop the last one.
        if self.MultiplierPipe[2]["predicate"]:
            self.updateRegister(
                "x{}".format(self.MultiplierPipe[2]["targetReg"]),
                self.MultiplierPipe[2]["result"]
            )
        self.MultiplierPipe.pop()

        #### Branch Unit
        if self.PC >= len(instructionMemory):
            self.PC = self.PC
        else:
            self.PC = self.PC + 1
        
        if self.BranchPipe["predicate"]:
            if self.BranchPipe["opcode"] == "loop":
                if self.LC > 0:
                    self.updateRegister("LC", self.LC - 1)
                    self.PC  = self.BranchPipe["targetPC"]
            elif self.BranchPipe["opcode"] == "hw":
                if self.LC > 0:
                    self.updateRegister("LC", self.LC - 1)
                    self.updateRegister("RBB", self.RBB + 1)
                    self.updateRegister("p{}".format(self.renameRegister(32)), 1)
                    self.PC = self.BranchPipe["targetPC"]
                elif self.EC > 0:
                    self.updateRegister("EC", self.EC - 1)
                    self.updateRegister("RBB", self.RBB + 1)
                    self.updateRegister("p{}".format(self.renameRegister(32)), 0)
                    self.PC = self.BranchPipe["targetPC"]
                else:
                    self.updateRegister("p{}".format(self.renameRegister(32)), 0)

        


def main():
    processor = VLIW470()

    # In the main loop, let's see what happens
    while True:
        processor.tick()

        if processor.PC >= len(instructionMemory):
            # ok, now it's possible to see a stop. do two more cycles.
            processor.tick()
            processor.tick()
            break
        
    # Finally, dump the state to the file
    json.dump(state, arg.result, indent=4)





if __name__ == "__main__":
    main()
