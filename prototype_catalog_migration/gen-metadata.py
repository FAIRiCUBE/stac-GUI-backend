#! /usr/bin/env python3
# -*- coding: UTF-8 -*-

import ast
import csv
import io
import os
import sys
import shutil

from copy import deepcopy
from datetime import datetime

from pygeometa.schemas.iso19139 import ISO19139OutputSchema

LANGUAGE = 'eng'

mcf_template = {
    'mcf': {
        'version': '1.0'
    },
    'metadata': {
        'language': LANGUAGE,
        'charset': 'utf8',
        'parentidentifier': 'TBD'
    },
    'spatial': {
        'datatype': 'grid',
        'geomtype': 'solid'
    },
    'identification': {
        'charset': 'utf8',
        'language': 'missing',
        'keywords': {},
        'status': 'onGoing',
        'maintenancefrequency': 'continual'
    },
    'content_info': {
        'type': 'image',
        'dimensions': []
    },
    'contact': {
      'pointOfContact': {},
      'distributor': {}
    },
    'distribution': {}
}


def generate_metadata(rec):
    mcf = deepcopy(mcf_template)
    now = datetime.now().isoformat()

    mcf['metadata']['identifier'] = rec['ID']
    mcf['metadata']['hierarchylevel'] = 'dataset'
    mcf['metadata']['datestamp'] = now
    mcf['identification']['title'] = rec['Product']
    mcf['identification']['abstract'] = rec['Description']

    mcf['identification']['keywords']['default'] = {
        'keywords': ['dataset'],
        'keywords_type': 'theme'
    }

    mcf['identification']['dates'] = {
        'creation': now
    }


    try:
        polygon = ast.literal_eval(rec['Polygon'])
        bbox = [
            polygon[0][0][0],
            polygon[0][0][1],
            polygon[0][2][0],
            polygon[0][2][1],
        ]
    except SyntaxError:
        bbox = [-180, -90, 180, 90]

    print(bbox)

    mcf['identification']['extents'] = {
        'spatial': [{
            'bbox': bbox,
            'crs': 4326
        }],
        'temporal': [{
            'begin': rec['Start'],
            'end': rec['End']
        }]
    }


    iso_os = ISO19139OutputSchema()
    return iso_os.write(mcf)


if __name__ == '__main__':

    if len(sys.argv) < 2:
        print(f'Usage: {sys.argv[0]} </path/to/csv>')
        sys.exit(1)

    print('Creating output folder')
    if os.path.exists('output'):
        shutil.rmtree('output')
    os.makedirs('output')

    print('Parsing CSV')

    with open(sys.argv[1]) as csvfile:
        reader = csv.DictReader(csvfile)
        print('Generating and writing XML to disk')
        for row in reader:
            xml = generate_metadata(row)
            filename = f'output/{row["ID"]}.xml'
            with io.open(filename, 'w', encoding='utf-8') as fh:
                fh.write(xml)
