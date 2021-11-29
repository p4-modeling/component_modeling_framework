#! /bin/bash

git clone https://github.com/gallenmu/moongen
cd moongen
./build.sh
./setup-hugetlbfs.sh
