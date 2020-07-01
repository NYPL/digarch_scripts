#!/bin/bash
find /Volumes/Staging/faComponents -type d -name 'photographs' > /Volumes/Staging/MISC/macphoto.txt
#parentname="$(basename "$(dirname "$PWD")")"
#echo $parentname
#echo $PWD
	while read line; do {
         printf 'cd %s
parentname="$(basename "$(dirname "$PWD")")"
mv ../photographs/ ../"$parentname"_photographs
mkdir -p {metadata/submissionDocumentation,objects}
mv -nv *.JPG objects/ | tee -a /Volumes/Staging/MISC/photosip.log
find /Volumes/Staging/photographs -name "$parentname"*.JPG -exec cp -nv {} objects/  > >(tee -a /Volumes/Staging/MISC/photosip.log) \;
' $line
	}
	done </Volumes/Staging/MISC/macphoto.txt> "/Volumes/Staging/MISC/photosip.sh"

	#bash "/Volumes/Staging/MISC/photosip".sh

	#rm "/Volumes/Staging/MISC/photosip".txt
	#rm "/Volumes/Staging/MISC/photosip".sh
	#echo -e "${BLUE}The photograph SIPS for faComponents have been packaged.${NC}"
#else
	#echo -e "${BLUE}Please try again.${NC}" && exit 1

