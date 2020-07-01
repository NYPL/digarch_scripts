#!/bin/bash

#This is a program to create dfxml or siefgried.csv for a collection.

BLUE='\033[0;36m'
NC='\033[0m'
PURPLE='\033[0;35m'
echo -e "${BLUE}This script will create dfxml for each item.${NC}"
echo -e "${PURPLE}Please enter your collection number in the M##### format:${NC}"

read collection

if [[ "$PWD" =~ "$collection" ]]

then

	ls -1 --ignore=*.txt >"$collection".txt
printf '#!/bin/bash\n
BLUE="\033[0;36m"\n
NC="\033[0m"\n
PURPLE="\033[0;35m"\n' > "$collection".sh	
	while read line; do {
		printf '
cd %s/objects
pwd
if disktype %s.001 | grep -q "HFS"; then
  brunnhilde.py -adnr --hfs %s.001 ~/ %s && echo -e "${PURPLE}HFS${NC}"
  mv ~/%s/siegfried.csv ../metadata/%s.csv
else
  brunnhilde.py -adnr %s.001 ~/ %s && echo -e "${BLUE}MFM${NC}"
  mv ~/%s/dfxml.xml ../metadata/%s.xml
fi


cd ../../
' $line $line $line $line $line $line $line $line $line $line
	}
	done <"$collection".txt>> "$collection".sh

	rm "$collection".txt

	bash "$collection".sh

	rm "$collection".sh
	echo -e "${BLUE}The disk images for $collection have dfxml.${NC}"
else
	echo -e "${BLUE}Please change into the collection directory and try again.${NC}" && exit 1
fi
