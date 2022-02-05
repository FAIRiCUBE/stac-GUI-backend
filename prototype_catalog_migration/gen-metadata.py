#! /usr/bin/env python3
# -*- coding: UTF-8 -*-

import ast
from copy import deepcopy
import csv
from datetime import datetime
import io
import os
import sys
import shutil
from urllib.parse import urlparse

from pygeometa.schemas.iso19139_2 import ISO19139_2OutputSchema

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
        'dates': {},
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

statuses = {
    'COMPLETED': 'completed',
    'ONGOING': 'onGoing',
    'Planned': 'planned',
}


def generate_metadata(rec):
    mcf = deepcopy(mcf_template)
    now = datetime.now().isoformat()

    mcf['metadata']['identifier'] = rec['ID']
    mcf['metadata']['hierarchylevel'] = 'dataset'
    mcf['metadata']['datestamp'] = now
    mcf['identification']['title'] = rec['Product']
    mcf['identification']['abstract'] = rec['Description']
    mcf['identification']['status'] = statuses[rec['Status']]

    mcf['identification']['keywords']['default'] = {
        'keywords': rec['Variable'],
        'keywords_type': 'theme'
    }
    mcf['identification']['keywords']['theme1'] = {
        'keywords': rec['Theme1'],
        'keywords_type': 'theme'
    }

    if rec['DOI']:
        doi_url = urlparse(rec['DOI'])
        mcf['identification']['doi'] = doi_url.path.lstrip('/')

    if row['Region']:
        mcf['identification']['keywords']['region'] = {
            'keywords': rec['Region'],
            'keywords_type': 'theme'
        }

    if row['Released'] not in [None, 'Planned']:
        mcf['identification']['dates'] = {
            'publication': row['Released']
        }

    try:
        polygon = ast.literal_eval(rec['Polygon'])
        bbox = [
            polygon[0][0][0],
            polygon[0][0][1],
            polygon[0][2][0],
            polygon[0][2][1],
        ]
    except (SyntaxError, TypeError):
        bbox = [-180, -90, 180, 90]

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

    mcf['acquisition'] = {
        'platforms': [{
            'identifier': row['EO_Missions']
        }]
    }

    mcf['distribution'] = {
        'website': {
            'url': row['Website'],
            'type': 'WWW:LINK',
            'name': 'website',
            'description': 'website',
            'function': 'information'
        }
    }

    if row['Access']:
        mcf['distribution']['access'] = {
            'url': row['Access'],
            'type': 'WWW:LINK',
            'name': 'access',
            'description': 'access',
            'function': 'download'
        }

    if row['Documentation']:
        mcf['identification']['url'] = row['Documentation']

    iso_os = ISO19139_2OutputSchema()
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
