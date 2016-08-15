from __future__ import absolute_import, unicode_literals, division, print_function

__author__ = 'reyrodrigues'

from .formhub_utils import generate_export, generate_sections
from pyxform import create_survey_element_from_dict
import requests
from collections import OrderedDict
import math

ONA_API_URL = "https://kc.humanitarianresponse.info/api/v1"


def title_dictionary(children, parent_index=None):
    return_items = []
    for index, item in enumerate(children):
        if parent_index:
            name_index = "{}.{}".format(parent_index, str(index + 1).zfill(2))
        else:
            name_index = "{}".format(str(index + 1).zfill(2))

        if 'label' in item and 'name' in item:
            if 'English' in item['label']:
                return_items.append((item['name'], "{} {}".format(name_index, item['label']['English'])))
            else:
                return_items.append((item['name'], "{} {}".format(name_index, item['label'])))

        if 'children' in item and item['type'] == 'group':
            return_items += title_dictionary(item['children'], name_index)

    return set(return_items)


def generate_joined(pk, token, output):
    from tempfile import NamedTemporaryFile
    import xlrd
    import subprocess, urllib
    ona_api_url = ONA_API_URL
    headers = {"Authorization": "Token {}".format(token)}

    if ona_api_url.endswith('/'):
        ona_api_url = ona_api_url[:-1]

    r = requests.get("{}/forms/{}.xlsx".format(ona_api_url, pk), headers=headers, stream=True)
    content = {}
    with NamedTemporaryFile(suffix='.xlsx') as temp:
        b =r.raw.read()
        temp.write(b)
        temp.flush()
        temp.delete = True

        rd = xlrd.open_workbook(temp.name)


    for name in rd.sheet_names():
        content[name] = []
        sheet = rd.sheet_by_name(name)
        headers = [sheet.cell_value(0, c) for c in xrange(0, sheet.ncols)]
        for row in range(1, sheet.nrows):
            values = [sheet.cell_value(row, c) for c in xrange(0, sheet.ncols)]
            content[name].append(OrderedDict(zip(headers, values)))

    for key, value in content.iteritems():
        if value:
            # _parent_table_name	_parent_index
            if '_parent_table_name' in value[0]:
                for r in value:
                    parent_table = r['_parent_table_name']
                    parent_index = r['_parent_index']

                    if parent_table in content:
                        parent_row = [pr for pr in content[parent_table] if parent_index == pr['_index']]
                        if parent_row:
                            parent_row = parent_row[0]
                            key_dictionary = [(parent_table + '/' + k, parent_row[k]) for k in parent_row.keys()]
                            r.update(dict(key_dictionary))

    import xlsxwriter

    w = xlsxwriter.Workbook(output.name)

    for key, value in content.iteritems():
        ws = w.add_worksheet(key)

        columns = list(value[0].keys()) # list() is not need in Python 2.x

        for j, col in enumerate(columns):
            ws.write(0, j, col)

        for i, row in enumerate(value, start=1):
            for j, col in enumerate(columns, start=1):
                ws.write(i, j, row[col])

    w.close()
    output.flush()


def do_work(pk, token):
    ona_api_url = ONA_API_URL
    headers = {"Authorization": "Token {}".format(token)}

    if ona_api_url.endswith('/'):
        ona_api_url = ona_api_url[:-1]

    data = requests.get("{}/data/{}".format(ona_api_url, pk), headers=headers).json()
    definition = requests.get("{}/forms/{}/form.json".format(ona_api_url, pk), headers=headers).json()

    xform_survey = create_survey_element_from_dict(definition)

    data = generate_export(definition, data, xform_survey=xform_survey)
    sections = generate_sections(definition)

    td = OrderedDict(title_dictionary(definition['children']))
    dict_copy = td.copy()
    keys_copy = list(td.keys())

    for item in td.keys():
        value = td[item]
        keys = [k for k in keys_copy if value == dict_copy[k]]

        if len(keys) <= 1:
            continue

        keys.sort()

        fill = math.ceil(math.log(len(keys), 10))

        # td[item] = "{} ({})".format(value, str(keys.index(item) + 1).zfill(int(fill)))
        td[item] = "{} ({})".format(value, item)

    for key, data_set in data.iteritems():
        section = sections[key]
        for s in section:
            for d in data_set:
                if s['xpath'] in d:
                    name = d[s['xpath']]
                    simplified_name = s['xpath'].split('/')[-1]

                    if s['type'] in ['select', 'select1']:

                        if s['type'] == 'select1':
                            option = [l['label']['English'] if isinstance(l['label'], dict) else l['label']
                                      for l in s['children']
                                      if isinstance(l, dict) and l['name'] == name]
                            if option:
                                option = option.pop()
                                d[s['xpath']] = option
                            elif 'itemset' in s and s['itemset']:
                                choices = xform_survey.choices.get(s['itemset'])
                                if choices:
                                    option = [l['label']['English'] if isinstance(l['label'], dict) else l['label']
                                              for l in choices
                                              if isinstance(l, dict) and l['name'] == name]
                                    if option:
                                        option = option.pop()
                                        d[s['xpath']] = option
                            else:
                                print(name, " not found")
                        else:
                            name = name.split(' ')
                            options = [l['label']['English'] if isinstance(l['label'], dict) else l['label']
                                       for l in s['children']
                                       if isinstance(l, dict) and l['name'] in name]
                            # print("Options", options)
                            if options:
                                d[s['xpath']] = ", ".join(options)
                            elif 'itemset' in s and s['itemset']:
                                choices = xform_survey.choices.get(s['itemset'])
                                if choices:
                                    options = [l['label']['English'] if isinstance(l['label'], dict) else l['label']
                                               for l in choices
                                               if isinstance(l, dict) and l['name'] == name]
                                    if options:
                                        d[s['xpath']] = ", ".join(options)

                    intermediate = d[s['xpath']]
                    del d[s['xpath']]

                    if simplified_name in td:
                        d[td[simplified_name]] = intermediate
                    else:
                        d[simplified_name] = intermediate

    section_name = data.keys()[0]

    return data


def kobo_to_excel(pk, token, file_name):
    import pandas

    data = do_work(pk, token)

    for k in data.keys():
        data[k.replace('/', '__')] = data.pop(k)

    writer = pandas.ExcelWriter(file_name)
    for key in data.keys():
        df = pandas.DataFrame.from_dict(data[key])
        if 'instanceID' in df:
            df = df.set_index('instanceID').sort_values(by='start')
        df.to_excel(writer, sheet_name=key[0:31])
    writer.save()


def fetch_api_key(username, password):
    ona_api_url = ONA_API_URL
    response = requests.get("{}/user".format(ona_api_url), auth=(username, password))

    data = response.json()

    if 'api_token' not in data:
        raise Exception(data)

    return data['api_token']
