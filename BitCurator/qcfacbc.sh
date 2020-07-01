#!/bin/bash

#This is a program to repackage SIP folders for a collection.
#find and cd not working on bc
BLUE='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}This script will repackage SIPs for each item.${NC}"
echo -e "${BLUE}Please enter your collection number in the M##### format:${NC}"

read collection

if [[ "$PWD" =~ "$collection" ]]

then

find . -maxdepth 1 -type d -name '*ER*' -printf '%P\n' > $collection.txt 
printf '#!/bin/bash\n' > $collection.sh		
	
	while read line; do {
         printf 'cd %s
collection="$(basename "$(dirname "$PWD")")"
if [ -n "$(find /metadata -maxdepth 1 -name "%s.csv")" ]
then
	cd /media/sf_Staging/faComponents/$collection
	echo -e "metadata/%s.csv present." |tee -a /media/sf_Staging/MISC/qcfac.log

elif [ -n "$(find /metadata/submissionDocumentation -maxdepth 1 -name "%s.csv")" ]
then
	mv -nv metadata/submissionDocumentation/"%s.csv" metadata/"%s.csv" |tee -a /media/sf_Staging/MISC/qcfac.log
	cd /media/sf_Staging/faComponents/$collection 
	echo -e "metadata/submissionDocumentation/%s.csv moved to metadata."
 
elif [ -n "$(find . -maxdepth 1 -name "%s.csv")" ] 
then 
	mv -nv "%s.csv" metadata/"%s.csv" |tee -a /media/sf_Staging/MISC/qcfac.log
	cd /media/sf_Staging/faComponents/$collection
	echo -e "%s.csv moved to metadata."
	
fi

cd /media/sf_Staging/faComponents/$collection
' $line $line $line $line $line $line $line $line $line $line $line 
	}
	done <"$collection".txt>> "$collection".sh
printf 'if [ -n "$(find . -maxdepth 1 -type d -name "$collection"_photographs)" ]
then
	cd /media/sf_Staging/faComponents
	echo -e "$collection_photographs is present." |tee -a /media/sf_Staging/MISC/photosip.log
elif [ -n "$(find . -maxdepth 1 -type d -name photographs)" ]
then
	mv photographs/ "$collection"_photographs
	mkdir -p "$collection"_photographs/{metadata/submissionDocumentation,objects}
	mv -nv "$collection"_photographs/*.JPG objects/ | tee -a /media/sf_Staging/MISC/photosip.log
	find /media/sf_Staging/photographs -name "$collection"*.JPG -exec cp -nv {} "$collection"_photographs/objects/  > >(tee -a /media/sf_Staging/MISC/photosip.log) \;
	cd /media/sf_Staging/faComponents
	echo -e "${BLUE}The photograph SIPS for $collection have been repackaged.${NC}"
elif [ -z "$(find . -maxdepth 1 -type d -name photographs)" ]
then
	mkdir -p "$collection"_photographs/{metadata/submissionDocumentation,objects}
	mv -nv "$collection"_photographs/*.JPG objects/ | tee -a /media/sf_Staging/MISC/photosip.log
	find /media/sf_Staging/photographs -name "$collection"*.JPG -exec cp -nv {} "$collection"_photographs/objects/  > >(tee -a /media/sf_Staging/MISC/photosip.log) \;
	cd /media/sf_Staging/faComponents
	echo -e "${BLUE}The photograph SIPS for $collection have been packaged.${NC}"
fi' >> $collection.sh
#	bash "$collection".sh

#	rm "$collection".txt
#	rm "$collection".sh
	echo -e "${BLUE}The folders for $collection have been repackaged.${NC}"
else
	echo -e "${BLUE}Please change into the collection directory and try again.${NC}" && exit 1
fi
