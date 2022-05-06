# XML Transformer for FTK to ArchivesSpace Transfer

This script transforms the generic XML output of Forensic Toolkit into a JSON file that can be easily ingested by an ArchivesSpace plugin. The JSON file captures series/file hierarchies, series titles, and file extents, all of which are imported to ArchiveSpace. 

## Dependencies

This script uses the lxml library to parse XML files from FTK. lxml can be installed using pip.

	pip install lxml

More information on lxml can be at [https://lxml.de/index.html]. 

Otherwise, the script only uses the built-in Python libraries. It was written with Python 3.8.5.

## Usage

The script expects two arguments: the file to be transformed and a desination file for the JSON output. Both arguments are required. 

## XML Parsing

The script functions by parsing and transforming a generic (not EAD) XML output. This means to make strong assumptions about where to look for information. It is possible that some configurations for FTK outputs will not include this information. For the script to work, the following information must be found in the following locations: 

 	``'/fo:root/fo:page-sequence[@master-reference="TOC"]/fo:flow'



## Common Issues

