#!/bin/bash

#This is a program to create checksums for transfer media files and identifty duplicate media.

BLUE='\033[0;36m'
NC='\033[0m'
echo $(date)
echo -e "${BLUE}This script will create Sha1 for a Media Item.${NC}"
echo -e "${BLUE}Please drag the Media Item icon over this window. See the Media Item path displayed? Hit return!:${NC}"

read CD

echo -e "${BLUE}Please enter the MediaID for this Media Item and hit return:${NC}"

read MediaID
#remove - and disk# to create collection#
Collection=${MediaID%-*}
#echo -e $Collection

if [ -z "$(find /Volumes/Staging/MISC/ -maxdepth 1 -name "$Collection.sha1")" ]
 then
	sha1deep -r "$CD" >>/Volumes/Staging/MISC/$Collection.sha1
fi
if [ -z "$(sha1deep -rx /Volumes/Staging/MISC/$Collection.sha1 "$CD")" ]
then
	echo -e "${BLUE}DUPLICATE!!!${NC}" && exit 1 
else
	#add new hashes to hash manifest
	sha1deep -r "$CD" >>/Volumes/Staging/MISC/$Collection.sha1
fi
echo $(date)