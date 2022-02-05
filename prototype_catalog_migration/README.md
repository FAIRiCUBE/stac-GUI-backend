# EOEPCA OSC

This code is to help initialize the Open Data Science Catalogue


```bash
# install the Python requirements
pip install -r requirements.txt

# run the process
python3 gen-metadata.py Projects-2021-12-20.csv Products-2021-12-20.csv Themes.csv Variables.csv Missions-2021-12-20.csv 
```

The process should take approximately 30 seconds, and will create an
`output` directory with:

- ISO 19115 files for all projects
- ISO 19115-2 files for all products
- ISO 19115 codelist catalogue (`codelists.xml`) for all themes, variables,
  and EO missions

Run the following command to import to pycsw:

```bash
pycsw-admin.py load-records --config default.cfg --path /path/to/records
```
