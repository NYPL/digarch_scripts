#!/bin/bash
#this is a program that moves metadata files into the /metadata folder 

BLUE='\033[0;36m'
GREEN='\033[1;32m'
RED='\033[0:31m'
NC='\033[0m'



find . -name '*.cue' -or -name '*.csv' -or -name '*.txt' > tempfile | md5deep -f tempfile > ./tempchecksums

echo -e "${GREEN}1. Checksums created.${NC}"

for f in `find . -name "*.cue"`; do 
	collnum=`echo "$f" | cut -d \. -f 2 | cut -d \/ -f 2 | cut -d \- -f 1`
	directory=`echo "$f" | cut -d \. -f 2 | cut -d \/ -f 2`
	mv $f /Volumes/Staging/ingest/diskImages/$collnum/$directory/metadata
	
done

for f in `find . -name "*.txt"`; do 
	collnum=`echo "$f" | cut -d \. -f 2 | cut -d \/ -f 2 | cut -d \- -f 1`
	directory=`echo "$f" | cut -d \. -f 2 | cut -d \/ -f 2`
	mv $f /Volumes/Staging/ingest/diskImages/$collnum/$directory/metadata
	
done

for f in `find . -name "*.log"`; do 
	collnum=`echo "$f" | cut -d \. -f 2 | cut -d \/ -f 2 | cut -d \- -f 1`
	directory=`echo "$f" | cut -d \. -f 2 | cut -d \/ -f 2`
	mv $f /Volumes/Staging/ingest/diskImages/$collnum/$directory/metadata
	
done

for f in `find . -name "*.csv"`; do 
	collnum=`echo "$f" | cut -d \. -f 2 | cut -d \/ -f 2 | cut -d \- -f 1`
	directory=`echo "$f" | cut -d \. -f 2 | cut -d \/ -f 2`
	mv $f /Volumes/Staging/ingest/diskImages/$collnum/$directory/metadata
	
done

echo -e "${GREEN}2. Metadata has been moved.${NC}"

collnum=`pwd | cut -d \/ -f 6`
directory=`pwd | cut -d \/ -f 7`

cd /Volumes/Staging/ingest/diskImages/$collnum/$directory/metadata

md5deep -x /Volumes/Staging/ingest/diskImages/$collnum/$directory/objects/tempchecksums *
	if [[ $(ls -A) ]]; then
		echo -e "${GREEN}2. Checksums validated.${NC}"
	else 
		echo -e "${RED}Checksums failed.${NC}"
fi

rm /Volumes/Staging/ingest/diskImages/$collnum/$directory/objects/tempfile
rm /Volumes/Staging/ingest/diskImages/$collnum/$directory/objects/tempchecksums 