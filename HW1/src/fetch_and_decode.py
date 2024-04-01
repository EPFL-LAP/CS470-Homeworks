import json
from typing import Optional
from data_structures import *


class Fetcher():
    def __init__(self, filename):
        self.filename = filename
        self.pc = 0

        # We store the entire parsed file in memory for convenience purposes
        with open(filename, 'r') as f:
            self.instructions = json.load(f)

    def fetch(self):
        num_ops = min(len(self.instructions) - self.pc, 4)
        instructions = []
        if self.pc < len(self.instructions):
            for i in range(num_ops):
                instructions.append(f'{self.pc+i} ' + self.instructions[self.pc+i])

            self.pc += num_ops
            return instructions
        else:
            return []


class Decoder():

    def __decode_one(self, ins):
        parts = [c.strip(',') for c in ins.split()]
        pc = int(parts[0])
        opcode = parts[1]
        rd = int(parts[2][1:])
        rs1 = int(parts[3][1:])
        rs2 = None
        imm = None
        # We are operating on immediate values
        if opcode[-1] == 'i':
            imm = parts[4]
            opcode = parts[1][:-1]
        else:
            rs2 = int(parts[4][1:])
        return Instruction(pc, opcode, rd, rs1, rs2, imm)

    def decode(self, instructions):
        decoded = []
        for ins in instructions:
            decoded.append(self.__decode_one(ins))
        return decoded




class FetchAndDecodeUnit():
    def __init__(self, filename, data_structures):
        self.fetcher = Fetcher(filename)
        self.decoder = Decoder()
        self.ds = data_structures

    def run(self):
        if self.ds.exception_flag:
            self.ds.program_counter = 0x10000
            self.fetcher.pc = 0x10000
            self.ds.dir = DecodedInstructionRegister()
            return

        DIR = DecodedInstructionRegister()
        DIR.buffer = self.ds.dir.buffer
        DIR.pcs = self.ds.dir.pcs
        DIR.backpressure = self.ds.dir.backpressure
        #TODO: Exception recovery: consider the ExceptionFlag and set the
        if not DIR.backpressure:
            ins = self.fetcher.fetch()
            decoded = self.decoder.decode(ins)
            DIR.fill(decoded)
        self._latch(DIR)

    def _latch(self, DIR):
        #As this is backpressure, this is the only field that needs to be updated from the other side of the pipeline
        DIR.backpressure = self.ds.dir.backpressure
        self.ds.dir = DIR
        self.ds.program_counter = self.fetcher.pc


