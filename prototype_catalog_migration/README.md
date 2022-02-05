# EOEPCA OSC

This code is to help initialize the Open Data Science Catalogue

```bash
pip install -r requirements.txt
```

The execute the script with:

```bash
python3 gen-metadata.py Products-2021-12-20.csv
```

This will create an output folder with ISO-19115 xml files to import to pycsw with:

```bash
pycsw-admin.py load-records --config default.cfg --path /path/to/records
```
