#!/bin/bash

if [ -z $1 ]; then
  echo "how many days?!"
  exit 1
fi

if [ $1 -gt 0 ]; then
  ./report.py
else
  echo "that doesn't make sense!"
  exit 1
fi

DAYS=$1

#for i in {1..$1}; do echo ./report.py $i; done
if [ $1 -ge 2 ]; then
  for (( c=1; c<=$((DAYS-1)); c++ ))
  do
    ./report.py $c
  done
fi
