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
            return_items.append((item['name'], "{} {}".format(name_index, item['label'])))

        if 'children' in item and item['type'] == 'group':
            return_items += title_dictionary(item['children'], name_index)

    return set(return_items)


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
        df.to_excel(writer, sheet_name=key)
    writer.save()


def fetch_api_key(username, password):
    ona_api_url = ONA_API_URL
    response = requests.get("{}/user".format(ona_api_url), auth=(username, password))

    data = response.json()

    if 'api_token' not in data:
        raise Exception(data)

    return data['api_token']
