#!/bin/bash -
myairport=$(networksetup -listallhardwareports | grep -1 Wi-Fi | sed -n 3p | awk '{print $2}')

if [ $(ifconfig $myairport | grep status | awk '{print $2}') = 'active' ]; then
    networksetup -setairportpower $myairport off
    echo $'\e[33mdisable WLAN interface...\e[0m'
fi
sudo tmuxp load dropcheck.yml
