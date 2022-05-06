# XML Transformer for FTK to ArchivesSpace Transfer

This script transforms the generic XML output of Forensic Toolkit into a JSON file that can be easily ingested by an ArchivesSpace plugin. The JSON file captures series/file hierarchies, series titles, and file extents, all of which are imported to ArchivesSpace. 

## Dependencies

This script uses the lxml library to parse XML files from FTK. lxml can be installed using pip.

	pip install lxml

More information on lxml can be found at [https://lxml.de/index.html]. 

Otherwise, the script only uses the built-in Python libraries. It was written with Python 3.8.5.

## Usage

The script expects two arguments: the file to be transformed and a desination file for the JSON output. Both arguments are required. 

The JSON output has a title, child structure, where the final entry is the extent information for an electronic record.

		{
			'title' : 'Series I : Photographs',
			'children' : [{'title' : 'ER 1', 'file_count' : 1}, {'title' : 'ER2', 'file_count' : 2}]
		}

## XML Parsing

The script functions by parsing and transforming a generic (not EAD) XML output. This means it makes strong assumptions about where to look for information. It is possible that some configurations for FTK outputs will not include this information. This implementation of lxml uses the XPATH library to parse XML paths. For the script to work, the following information must be found in the following locations: 

 The script expects to find the record title and a page indentation for each block in the table of contents ("TOC"). 

 	'/fo:root/fo:page-sequence[@master-reference="TOC"]/fo:flow'

 The script expects to find a "ref-id" tag starting with "bk" here. 

 	con't from above: 'fo:basic-link/fo:page-number-citation'

 The script expects to find the extent information for each individual file in a record here. It looks for an "id" tag and a regular expression match with the logical size in bytes expressed "some number B" i.e. as "1000 B".

 	'/fo:root/fo:page-sequence[@master-reference="bookmarksPage"]/fo:flow/fo:table[@id]'

 The script looks here for the collection title. 

 	'/fo:root/fo:page-sequence[@master-reference="caseInfoPage"]/fo:flow/fo:table/fo:table-body/fo:table-row/fo:table-cell/fo:block/text()'


 Future improvements could consider how to effeciently validate whether the XML file conforms to the script's assumptions. 


## Common Issues

### lxml parsing returns empty cells

When the structure of the XML file changes, the most common result is that the parser will return empty cells that either break the script or result in inaccurate information. To troubleshoot, I recommend opening the XML file in Juypter Nsotebook and using lxml to either parse the string or use the .tostring method.

### performance issues for larger XML files

Because the each electronic record may have many individual files associated with it, using XPATH to evaluate the contents of each cell can slow the script down substantially. This implementation uses the .tostring method on each row in the transform_xml_tree function to improve performance. 

### duplication

The logic that nests the hierarchy tends to result in many duplicates being created. The script has a dedicated function for cleaning nested duplicates, but the implementation currently assumes that the first entry in the dictionary always reflects the correct depth for that series. It is important to check for this bug when transforming a report for the first time. 

The structure of the bug is as follows:

	{	
		"title_1: Series I,"
		"children_1" : {"title_2" : "Subseries I"},
		"title_2" : "Subseries I"
	}

### list logic

The script works by parsing the XML for the relevant archival information, storing it in a list, and transforming that list into a nested dictionary. Issues with extent values can typically be traced back to the transformations of list items while issues in the hierarchy can be traced to the dictionary nesting. 