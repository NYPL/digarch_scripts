#!/bin/bash

#This is a program to create SIP folders for a collection.

BLUE='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}This script will create SIP templates for each item.${NC}"
echo -e "${BLUE}Please enter your collection number in the M##### format:${NC}"

read collection

if [[ "$PWD" =~ "$collection" ]]

then

	echo -e "${BLUE}Please enter the number of the first item you'd like a folder made for:${NC}"

	read first

	echo -e "${BLUE}Please enter the last number:${NC}"

	read last

	for x in $(seq -f "%04g" $first $last)
	do 
	eval mkdir -p -v $collection-$x/{objects,metadata/submissionDocumentation}
	done

	echo -e "${BLUE}The folders for $collection have been built.${NC}"
else
	echo -e "${BLUE}Please change into the collection directory and try again.${NC}" && exit 1
fi