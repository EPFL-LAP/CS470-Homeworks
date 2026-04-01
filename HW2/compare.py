import os
import re
import json
import itertools
import argparse

parser = argparse.ArgumentParser()

parser.add_argument("--loop", required=False, help="The reference JSON using the loop instruction.", type=argparse.FileType("r"))
parser.add_argument("--pip", required=False, help="The reference JSON using the loop.pip instruction.", type=argparse.FileType("r"))
parser.add_argument("--refLoop", required=False, help="The reference loop JSON.", type=argparse.FileType("r"))
parser.add_argument("--refPip", required=False, help="The reference pip JSON.", type=argparse.FileType("r"))

RED = '\x1b[31m'
GREEN = '\x1b[36m'
RESET = '\x1b[0m'

ALU0 = 0
ALU1 = 1
MULT = 2
MEM = 3
Branch = 4

slotToStr = ["ALU0", "ALU1", "Mult", "Mem", "Branch"]

def swapALUs(bundle):
    alu0 = bundle[ALU0]
    bundle[ALU0] = bundle[ALU1]
    bundle[ALU1] = alu0

    return bundle

def rawInst(inst):
    p = re.compile(r"\s+")
    return re.sub(p, "", inst).lower()

def compareInstructions(resI, refI):
    rawResI = rawInst(resI)
    rawRefI = rawInst(refI)

    return rawResI == rawRefI

def compareBundles(resB, refB, bLoc):
    for iLoc, (resI, refI) in enumerate(itertools.zip_longest(resB, refB)):
        if((resI == None) or (refI == None)):
            return RED + "Bundle length does not match." + RESET

        if(not compareInstructions(resI, refI)):
            return RED + "Instruction do not match at bundle " + str(bLoc) + \
                ", instruction slot: " + slotToStr[iLoc] + ": " + \
                resI + " != " + refI + RESET

    return ""

def compare(resF, refF):
    registerEqu = {}

    for bLoc, (resB, refB) in enumerate(itertools.zip_longest(resF, refF)):
        if((resB == None) or (refB == None)):
            return "[" + RED + "Error" + RESET + "] Schedule length does not match."

        bOks = compareBundles(resB, refB, bLoc)
        bSwapOk = compareBundles(swapALUs(resB), refB, bLoc)

        if((bOks != "") and (bSwapOk != "")):
            return bOks

    return GREEN + "PASSED!" + RESET

args = parser.parse_args()

if(args.loop is not None):
    LOOP = json.load(args.loop)
    REFLOOP = json.load(args.refLoop)
    simpleFull = compare(LOOP, REFLOOP)
    print("loop schedule: " + simpleFull)

if(args.pip is not None):
    PIP = json.load(args.pip)
    REFPIP = json.load(args.refPip)
    pipFull = compare(PIP, REFPIP)
    print("loop.pip schedule: " + pipFull)

