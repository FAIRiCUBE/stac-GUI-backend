import ast
from copy import deepcopy
import csv
from datetime import datetime
import io
import os
import sys
import shutil
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader
from pygeometa.schemas.iso19139 import ISO19139OutputSchema
from pygeometa.schemas.iso19139_2 import ISO19139_2OutputSchema

LANGUAGE = 'eng'

MCF_TEMPLATE = {
    'mcf': {
        'version': '1.0'
    },
    'metadata': {
        'language': LANGUAGE,
        'charset': 'utf8'
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

PROJECTS = {}

STATUSES = {
    'COMPLETED': 'completed',
    'ONGOING': 'onGoing',
    'Planned': 'planned',
}

TEMPLATE_ENV = Environment(
    loader=FileSystemLoader(['.']),
    autoescape=True
)
CODELISTS_TEMPLATE = TEMPLATE_ENV.get_template('codelists.j2')


def build_theme_keywords(row):
    keywords = {
        'themes': {
            'keywords': [],
            'keywords_type': 'theme'
        }
    }

    for i in range(1, 7):
        column_name = f'Theme{i}'
        if column_name in row and row[column_name]:
            keywords['themes']['keywords'].append(row[column_name])

    return keywords


def generate_project_metadata(rec):
    mcf = deepcopy(MCF_TEMPLATE)
    now = datetime.now().isoformat()

    identifier = f'project-{rec["Project_ID"]}'

    mcf['metadata']['identifier'] = identifier
    mcf['metadata']['hierarchylevel'] = 'datasetcollection'
    mcf['metadata']['datestamp'] = now
    mcf['identification']['title'] = rec['Project_Name']
    mcf['identification']['abstract'] = rec['Short_Description']
    mcf['identification']['status'] = STATUSES[rec['Status']]

    mcf['identification']['keywords']['themes'] = build_theme_keywords(rec)

    mcf['identification']['keywords']['short-name'] = {
        'keywords': rec['Short_Name'],
        'keywords_type': 'theme'
    }

    mcf['identification']['extents'] = {
        'spatial': [{
            'bbox': [-180, -90, 180, 90],
            'crs': 4326
        }],
        'temporal': [{
            'begin': rec['Start_Date_Project'],
            'end': rec['End_Date_Project']
        }]
    }

    mcf['contact']['pointOfContact'] = {
        'organization': rec['Consortium'],
        'individualname': rec['TO'],
        'email': rec['TO_E-mail']
    }

    mcf['distribution'] = {
        'website': {
            'url': rec['Website'],
            'type': 'WWW:LINK',
            'name': 'website',
            'description': 'website',
            'function': 'information'
        }
    }

    if rec['Eo4Society_link']:
        mcf['identification']['url'] = rec['Eo4Society_link']

    iso_os = ISO19139OutputSchema()
    return identifier, rec['Project_Name'], iso_os.write(mcf)


def generate_product_metadata(rec, parent_id=None):
    mcf = deepcopy(MCF_TEMPLATE)
    now = datetime.now().isoformat()

    identifier = f'project-{rec["ID"]}'

    mcf['metadata']['identifier'] = identifier
    mcf['metadata']['hierarchylevel'] = 'dataset'
    mcf['metadata']['datestamp'] = now
    mcf['identification']['title'] = rec['Product']
    mcf['identification']['abstract'] = rec['Description']
    mcf['identification']['status'] = STATUSES[rec['Status']]

    if parent_id is not None:
        mcf['identification']['parenidentifier'] = parent_id

    mcf['identification']['keywords']['default'] = {
        'keywords': rec['Variable'],
        'keywords_type': 'theme'
    }

    mcf['identification']['keywords']['themes'] = build_theme_keywords(row)

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
    return identifier, iso_os.write(mcf)


if __name__ == '__main__':

    if len(sys.argv) < 6:
        print(f'Usage: {sys.argv[0]} </path/to/projects.csv> </path/to/products.csv </path/to/themes.csv> </path/to/variables.csv> </path/to/eo_missions.csv')  # noqa
        sys.exit(1)

    print('Creating output folder')
    if os.path.exists('output'):
        shutil.rmtree('output')
    os.makedirs('output')

    print('Generating metadata')
    print('Parsing Projects CSV')
    with open(sys.argv[1]) as csvfile:
        reader = csv.DictReader(csvfile)
        print('Generating and writing XML to disk')
        for row in reader:
            identifier, project_name, xml = generate_project_metadata(row)
            PROJECTS[project_name] = identifier
            filename = f'output/{identifier}.xml'
            with io.open(filename, 'w', encoding='utf-8') as fh:
                fh.write(xml)

    print('Parsing Products CSV')
    with open(sys.argv[2]) as csvfile:
        reader = csv.DictReader(csvfile)
        print('Generating and writing XML to disk')

        for row in reader:
            parent_id = None
            if row['Project'] in PROJECTS:
                parent_id = PROJECTS[row['Project']]

            identifier, xml = generate_product_metadata(row, parent_id)
            filename = f'output/{identifier}.xml'
            with io.open(filename, 'w', encoding='utf-8') as fh:
                fh.write(xml)

    print('Generating codelists')
    codelists = {
        'themes': {
            'identifier': 'Theme',
            'description': 'Themes',
            'entries': []
        },
        'variables': {
            'identifier': 'Variable',
            'description': 'Variables',
            'entries': []
        },
        'eo_missions': {
            'identifier': 'EO_Mission',
            'description': 'EO Missions',
            'entries': []
        }
    }

    print('Parsing Themes CSV')
    with open(sys.argv[3]) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            codelists['themes']['entries'].append({
                'identifier': row['theme'],
                'description': row['description'],
                'url': row['link']
            })

    print('Parsing Variables CSV')
    with open(sys.argv[4]) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            codelists['variables']['entries'].append({
                'identifier': row['variable'],
                'description': row['variable description'],
                'url': row['link']
            })

    print('Parsing EO Missions CSV')
    with open(sys.argv[5]) as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            codelists['eo_missions']['entries'].append({
                'identifier': row[0],
                'description': row[0]
            })

    print('Generating and writing XML to disk')
    codelist_xml = CODELISTS_TEMPLATE.render(codelists=codelists)
    with io.open('output/codelists.xml', 'w', encoding='utf-8') as fh:
        fh.write(codelist_xml)
