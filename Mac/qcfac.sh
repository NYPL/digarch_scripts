#!/bin/bash

#This is a program to repackage SIP folders for a collection.

BLUE='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}This script will repackage SIPs for each item.${NC}"
echo -e "${BLUE}Please enter your collection number in the M##### format:${NC}"

read collection

if [[ "$PWD" =~ "$collection" ]]

then

#	find . -maxdepth 1 -type d -name '*ER*' -printf '%P\n' > $collection.txt 
		#how to remove 1st & last? add ER?
	
	while read line; do {
         printf 'cd %s
collection="$(basename "$(dirname "$PWD")")"
if [ -n "$(find /Volumes/Staging/faComponents/$collection/%s/metadata -maxdepth 1 -name "%s.csv")" ]
then
	cd /Volumes/Staging/faComponents/$collection
	echo -e "metadata/%s.csv present." |tee -a /Volumes/Staging/MISC/qcfac.log

elif [ -n "$(find /Volumes/Staging/faComponents/$collection/%s/metadata/submissionDocumentation -maxdepth 1 -name "%s.csv")" ]
then
	mv -nv metadata/submissionDocumentation/"%s.csv" metadata/"%s.csv" |tee -a /Volumes/Staging/MISC/qcfac.log
	cd /Volumes/Staging/faComponents/$collection 
	echo -e "metadata/submissionDocumentation/%s.csv moved to metadata."
 
elif [ -n "$(find /Volumes/Staging/faComponents/$collection/%s -maxdepth 1 -name "%s.csv")" ] 
then 
	mv -nv "%s.csv" metadata/"%s.csv" |tee -a /Volumes/Staging/MISC/qcfac.log
	cd /Volumes/Staging/faComponents/$collection
	echo -e "%s.csv moved to metadata."
	
fi
' $line $line $line $line $line $line $line $line $line $line $line $line $line $line
	}
	done <"$collection".txt> "$collection".sh

	bash "$collection".sh

	rm "$collection".txt
	rm "$collection".sh
	echo -e "${BLUE}The folders for $collection have been repackaged.${NC}"
else
	echo -e "${BLUE}Please change into the collection directory and try again.${NC}" && exit 1
fi