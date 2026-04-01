#!/bin/bash

./build.sh

for tnum in ./given_tests/*
do
    ./run.sh $tnum/input.json $tnum/simple.json $tnum/pip.json
done

