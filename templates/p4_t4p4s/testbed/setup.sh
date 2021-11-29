#!/bin/bash

{% if testbed_manual %}
# NOTE: this script is written to work with the pos testbed controller
# these are the steps required to perform the measurement
# to work in another testbed, replace the pos_* calls with respective implementations
{% endif %}

# Set debug stuff
set -x

# Set noninteractive shell
export DEBIAN_FRONTEND="noninteractive"

# dependencies
apt-get update -y --allow-releaseinfo-change
apt-get upgrade -y
apt-get autoremove -y
apt-get clean -y
apt-get install sudo python3-pip python-ujson psmisc linux-cpupower net-tools netcat -y
apt-get install linux-perf -y

### tapas setup
TAPAS_COMMIT_BOOTSTRAP=$(pos_get_variable tapas/git/bootstrap_commit)
TAPAS_COMMIT=$(pos_get_variable tapas/git/commit)
P4C_COMMIT=$(pos_get_variable versions/p4c)
HLIR_COMMIT=$(pos_get_variable versions/hlir16)
DPDK_VERSION=$(pos_get_variable versions/dpdk)
P4RUNTIME_COMMIT=$(pos_get_variable versions/p4runtime)
PROTOBUF_COMMIT=$(pos_get_variable versions/protobuf)

# in case we download from our lrz gitlab instance
ssh-keyscan gitlab.lrz.de >> ~/.ssh/known_hosts
# download repo
git clone $(pos_get_variable tapas/git/url)
cd t4p4s
git checkout ${TAPAS_COMMIT_BOOTSTRAP}
git submodule update --init --recursive

# bootstrap t4p4s
DPDK_VSN=$DPDK_VERSION TAPAS_COMMIT=$TAPAS_COMMIT P4C_COMMIT=$P4C_COMMIT HLIR_COMMIT=$HLIR_COMMIT PROTOBUF_BRANCH=$PROTOBUF_COMMIT ./bootstrap-t4p4s.sh

# bind interfaces
cd ~
wget https://raw.githubusercontent.com/libmoon/libmoon/1dde068b9da43a416a23a371e9394c6d209991cd/bind-interfaces.sh
sed -i '32s/cd deps\/dpdk/cd \/root\/t4p4s\/dpdk-19.02/' bind-interfaces.sh
chmod +x bind-interfaces.sh
./bind-interfaces.sh

# set cpu frequency manipulation
FREQ=$(pos_get_variable max_cpu_frequency)
modprobe cpufreq_userspace
cpupower frequency-set --governor userspace
cpupower --cpu all frequency-set --freq ${FREQ}GHz
# disable turbo boost
echo 0 > /sys/devices/system/cpu/cpufreq/boost

# disable Simultaneous Multithreading control
echo off > /sys/devices/system/cpu/smt/control
