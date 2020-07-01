#!/bin/bash

#This is a program to create CMS metadata for file transfers.

BLUE='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}Please enter the MediaID for this CD and hit return:${NC}"

read MediaID
#remove - and disk# to create collection#
Collection=${MediaID%-*}
#echo -e $Collection
Bag=${MediaID}_bag
#echo -e $Bag
tree "/Volumes/Staging/ingest/fileTransfers/$Collection/$MediaID/objects/$Bag/data" | tail -1
du -ck "/Volumes/Staging/ingest/fileTransfers/$Collection/$MediaID/objects/$Bag/data" | tail -1