#!/bin/bash

#This is a program to repackage SIP folders for a collection.

BLUE='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}This script will repackage SIPs for each item.${NC}"
echo -e "${BLUE}Please enter your collection number in the M##### format:${NC}"

read collection

if [[ "$PWD" =~ "$collection" ]]

then

	ls -1 >"$collection".txt
	while read line; do {
         printf 'cd %s
pwd
bash /Volumes/Staging/MISC/movephotograph.sh 
cd objects
bash /Volumes/Staging/MISC/metadata.sh
cd ../../
' $line
	}
	done <"$collection".txt> "$collection".sh

	bash "$collection".sh

	rm "$collection".txt
	rm "$collection".sh
	echo -e "${BLUE}The folders for $collection have been repackaged.${NC}"
else
	echo -e "${BLUE}Please change into the collection directory and try again.${NC}" && exit 1
fi