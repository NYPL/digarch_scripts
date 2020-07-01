#!/bin/bash

#This is a program to create Siegfried metadata, bags and validation for file transfers.
#Check that sf conf file is set properly

BLUE='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}This script will create a file transfer.${NC}"
echo -e "${BLUE}Please drag the SIP folder over this window. See the folder path displayed? Hit return!:${NC}"

read FT

echo -e "${BLUE}Please enter the MediaID for this file transfer and hit return:${NC}"

read MediaID
#remove - and disk# to create collection#
Collection=${MediaID%-*}
#echo -e $Collection
Bag=${MediaID}_bag
#echo -e $Bag
#designate base path
FTpath="/Volumes/DigArchDiskStation/Staging/ingest/fileTransfers"
#create MediaID directory
mkdir -p "$FTpath/$Collection/$MediaID/"{metadata/submissionDocumentation,objects}
#create sf csv
sf "$FT" > "$FTpath/$Collection/$MediaID/metadata/$MediaID.csv"
#create bag, set to verbose output and exclude hidden files
bagit create "$FTpath/$Collection/$MediaID/objects/$Bag" "$FT" --verbose --excludehiddenfiles
#verify bag is complete
bagit verifycomplete "$FTpath/$Collection/$MediaID/objects/$Bag"
#verify payload checksums
bagit verifypayloadmanifests "$FTpath/$Collection/$MediaID/objects/$Bag"
#output number of files in payload
tree "$FTpath/$Collection/$MediaID/objects/$Bag/data" | tail -1
#output size of payload in kb
du -ck "$FTpath/$Collection/$MediaID/objects/$Bag/data" | tail -1