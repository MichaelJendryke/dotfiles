#!/bin/bash
echo "Running borg backup"
export BORG_PASSCOMMAND="cat $HOME/.borg-passphrase" 
borg create -C zlib,6 --exclude What/ --exclude '.Trash-1000' --exclude 'snap' --exclude '.local' --exclude '.cache' --progress /media/mj/USB_BORG/BORG/HOME/::{now:%Y-%m-%d} /home/mj
