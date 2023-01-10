#!/bin/bash
# Script to launch N clients simoultanesouly to retrieve content from the server
NUM_CLIENTS=$1
WORK_DIR='/home/gina/Documents/networking_project/twisted_based/clients'
echo 'Downloading ' $NUM_CLIENTS 'clients' 
cd $WORK_DIR
for (( i = 1; i <= $NUM_CLIENTS; i++ ))
do 
        echo "Downloading client $i on port 901$i"
        python3 client_udp.py -i $i -f file3Kb.txt -w 2 > log$i.txt & 
done
wait
