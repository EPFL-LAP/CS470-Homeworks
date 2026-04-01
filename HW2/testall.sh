#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
RESET='\033[0m'

i=1
for tnum in ./given_tests/*
do
    loopPassed=false
    loopColor=$RED

    for simple_ref in ${tnum}/simple_ref*.json
    do
        out="$(python compare.py --loop ${tnum}/simple.json --refLoop ${simple_ref})"
        passed=$(echo "$out" | head -n 1)

        if [[ "$passed" == *"PASSED"* ]]; then
            loopPassed=true
            loopColor=$GREEN
        fi
    done

    pipPassed=false
    pipColor=$RED

    for pip_ref in ${tnum}/pip_ref*.json
    do
        out="$(python compare.py --pip ${tnum}/pip.json  --refPip ${pip_ref})"
        passed=$(echo "$out" | head -n 1)

        if [[ "$passed" == *"PASSED"* ]]; then
            pipPassed=true
            pipColor=$GREEN
        fi
    done

    cat ${tnum}/desc.txt
    printf "passed loop:  ${loopColor}${loopPassed}${RESET} passed pip: ${pipColor}${pipPassed}${RESET}\n\n"


    i=$((i+1))
done

