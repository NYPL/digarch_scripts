#!/bin/bash
# this script copies JPEGS from photographs directory to submissionDocumentation in the MediaID directory.

BLUE='\033[0;36m'
GREEN='\033[1;32m'
RED='\033[0:31m'
NC='\033[0m'


collnum=`pwd | cut -d \/ -f 6`
directory=`pwd | cut -d \/ -f 7`
dir_path=$(pwd -P)
find /Volumes/Staging/photographs -name "$directory*.JPG" -exec cp {} $dir_path/metadata/submissionDocumentation \;

echo -e "${GREEN}Photograph(s) have been moved.${NC}"

