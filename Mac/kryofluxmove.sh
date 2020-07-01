#!/bin/bash
# this script moves kryoflux output for media item into objects folder and the log into a metadata folder.

BLUE='\033[0;36m'
GREEN='\033[1;32m'
RED='\033[0:31m'
NC='\033[0m'

echo -e  "${BLUE}Please enter your collection number to initiate the move.${NC}"

read collnum

#find . -name "$collnum-*" > tempfile | md5deep -f tempfile > /Volumes/Staging/ingest/kryofluxOutput/tempchecksums

#rm tempfile

#md5deep -r /Volumes/Staging/ingest/diskImages/$collnum > /Volumes/Staging/ingest/kryofluxOutput/tempchecksums2

#echo -e "${GREEN}1. Checksums created.${NC}"

#cat /Volumes/Staging/ingest/kryofluxOutput/tempchecksums2 >> /Volumes/Staging/ingest/kryofluxOutput/tempchecksums 

#find . -name "$collnum-*" | cp 

for f in `find . -name "$collnum-*.tar"`; do 
	directory=`echo "$f" | cut -d \. -f 2 | cut -d \/ -f 2`
	mv $f /Volumes/Staging/KFStreamArchive

done

for f in `find . -name "$collnum-*.001"`; do 
	directory=`echo "$f" | cut -d \. -f 2 | cut -d \/ -f 2`
	mv $f /Volumes/Staging/ingest/diskImages/$collnum/$directory/objects/

done

for f in `find . -name "$collnum-*.log"`; do 
	directory=`echo "$f" | cut -d \. -f 2 | cut -d \/ -f 2`
	mv $f /Volumes/Staging/ingest/diskImages/$collnum/$directory/metadata/

done

echo -e "${GREEN}Disk image has been transferred to diskIMages and steam files transferred to KFSteamArchive.${NC}"

#cd /Volumes/Staging/ingest/diskImages/$collnum

#md5deep -x /Volumes/Staging/ingest/kryofluxOutput/tempchecksums *

#if [[ $(ls -A) ]]; then
	

#	echo -e "${GREEN}3. Files have been validated.${NC}" 
#else 
	#echo -e "${RED}Validation failed.${NC}"
#fi

#rm /Volumes/Staging/ingest/kryofluxOutput/tempchecksums 

#rm /Volumes/Staging/ingest/kryofluxOutput/tempchecksums2

