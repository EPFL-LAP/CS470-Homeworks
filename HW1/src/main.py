#!/usr/bin/env python3

import argparse

import fetch_and_decode
import rename_and_dispatch
import issue
import commit
import json
from data_structures import *

def start_components(input_filename):
    ds = DataStructures()

    #Execute in the following order: Commit, Execution, Rename, Issue, Fetch

    comm = commit.CommitUnit(ds)
    exec = issue.ExecuteUnit(ds)
    rd = rename_and_dispatch.RenameAndDispatchUnit(ds)
    iss = issue.IssueUnit(ds)
    f = fetch_and_decode.FetchAndDecodeUnit(input_filename, ds)
    return ds, [exec, comm, iss, rd,  f]

def launch_simulation(input_filename, output_filename):
    ds, components = start_components(input_filename)
    state = []
    state.append(ds.dumpState())
    # for i in range(26):
    while True:
        for c in components:
            c.run()
        dp = ds.dumpState()
        state.append(dp)
        ds.cycle+=1
        if ds.dir.isEmpty() and ds.active_list.isEmpty() and not ds.exception_flag:
            break

    with open(output_filename, "w") as f:
        json.dump(state, f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_filename", type=str)
    parser.add_argument("output_filename", type=str)
    args = parser.parse_args()

    launch_simulation(args.input_filename, args.output_filename)

if __name__=='__main__':
    main()

    # launch_simulation("../given_tests/08/input.json", "sample_output")
    # launch_simulation("../given_tests/05/input.json")
