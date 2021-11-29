#! /bin/bash

apt update --allow-releaseinfo-change
apt install virtualenv zstd texlive-full -y

# set git details
git config --global user.name "Dominik Scholz"
git config --global user.email "scholz@net.in.tum.de"

# unpack archives
cd ../data
for filename in *.zst; do
	tar --zstd -xvf $filename
done
