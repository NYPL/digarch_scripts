# Extent reporting scripts

These scripts create JSON reports from either Forensic Toolkit XML output or hard drive directory structures that can be ingested into ArchivesSpace.
The JSON report captures series/file hierarchies, series titles, file size summaries, and file counts.

The JSON must conform to the following structure, with ER report occurring at any level:

```
{
	'title' : 'Series I ...',
	'children' : [
		{
			'title': 'Subseries A ...',
			children: [
				{
					'title': 'ER 1: ...',
					'er_number': 'ER 1',
					'er_name': '...',
					'file_size': int,
					'file_number': int
				},
				{...}
			]
		},
		{...}
	]
}
```

## Dependencies

`report_ftk_extents.py` uses the lxml library to parse XML files from FTK. lxml can be installed using pip.

	pip install lxml

More information on lxml can be found at [https://lxml.de/index.html].

Otherwise, scripts only use the built-in Python libraries. It was written with Python 3.8.5.

## Usage

### `report_ftk_extents.py`

The script requires two arguments:

1. the path to the FTK XML report
2. the path to a destination folder for the JSON report

#### XML Parsing

The script functions by parsing and transforming a generic FTK XML output.
This means it makes strong assumptions about where to look for information.
It is possible that some configurations for FTK outputs will not include this information.
This implementation of lxml uses the XPATH library to parse XML paths.
For the script to work, the following information must be found in the following locations.

The script expects to find the record title and a page indentation for each block in the table of contents ("TOC").

```xslt
/fo:root/fo:page-sequence[@master-reference="TOC"]/fo:flow
```

The script expects to find a "ref-id" tag starting with "bk" here.

```xslt
/fo:root/fo:page-sequence[@master-reference="TOC"]/fo:flow/fo:basic-link/fo:page-number-citation
```

The script expects to find the extent information for each individual file in a record here. It looks for an "id" tag and a regular expression match with the logical size in bytes expressed "some number B" i.e. as "1000 B".

```xslt
/fo:root/fo:page-sequence[@master-reference="bookmarksPage"]/fo:flow/fo:table[@id]
```

The script looks here for the collection title.

```xslt
/fo:root/fo:page-sequence[@master-reference="caseInfoPage"]/fo:flow/fo:table/fo:table-body/fo:table-row/fo:table-cell/fo:block/text()
```

Future improvements could consider how to effeciently validate whether the XML file conforms to the script's assumptions.

#### Common Issues

lxml parsing returns empty cells

When the structure of the XML file changes, the most common result is that the parser will return empty cells that either break the script or result in inaccurate information. To troubleshoot, I recommend opening the XML file in Juypter Notebook and using lxml to either parse the string or use the .tostring method.



### `report_hdd_extents.py`

The script requires two arguments:

1. the path to the folder of processed ERs on the hard drive
2. the path to an output folder for the JSON report

#### Hard Drive Parsing

The hard drive directory structure must match the finding aid structure hierarchy of series, subseries, components, etc.
