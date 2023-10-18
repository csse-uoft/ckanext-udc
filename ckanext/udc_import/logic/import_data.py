import re
import pandas as pd
import json as js
from datetime import datetime

import ckan.plugins.toolkit as toolkit
from ckan.types import Context
import ckan.logic as logic
import ckan.model as model
from ckan.common import current_user

from typing import List, Dict, cast


class DataPreprocessor:
    # rule 1: convert title to str with '-' separating values and hard constrain on length to be <= 100 chars
    @staticmethod
    def clean_title(title_name, max_length=100):
        title_name = re.sub(r"[^\w]+$", "", re.sub(r"[^\w]+", "-", title_name))
        title_name = title_name.lower()
        return title_name[:max_length]

    # rule 2: clean tags in required format
    @staticmethod
    def clean_tags(input_str):
        words = re.findall(r'\w+(?:\.\w+)*', str(input_str))
        tag_list = [{'name': word.capitalize()}
                    for word in words if len(word) > 1]
        return tag_list

    # rule 3: clean geospatial area in required format
    @staticmethod
    def clean_geo_span(input_str):
        words = re.findall(r'\w+', input_str)
        geo_area = ', '.join(word.capitalize() for word in words)
        return geo_area

    # rule 4: clean date and set to minimum in required format
    @staticmethod
    def clean_min_date(yyyy_mm_dd):
        yyyy_mm_dd = int(yyyy_mm_dd)
        date = datetime(yyyy_mm_dd, 1, 1).strftime('%Y-%m-%d')
        return date

    # rule 5: clean date and set to maximum in required format
    @staticmethod
    def clean_max_date(yyyy_mm_dd):
        yyyy_mm_dd = int(yyyy_mm_dd)
        date = datetime(yyyy_mm_dd, 12, 31).strftime('%Y-%m-%d')
        return date

    # rule 6: handling duplicate title names with different resource value
    @staticmethod
    def clean_and_append_numbers(df, column_name):
        # print('function called')
        title_counts = df[column_name].value_counts()
        # print('value counts executed')
        counter = {}

        def append_numbers(row):
            title = row[column_name]
            if title_counts[title] > 1:
                if title in counter:
                    counter[title] += 1
                    return f"{title} ({row['name']}) - {counter[title]}"
                else:
                    counter[title] = 1
                    return f"{title} ({row['name']}) - {counter[title]}"
            else:
                return f"{title} ({row['name']})"

        df[column_name] = df.apply(append_numbers, axis=1)


def load_data_to_ckan(data_dicts: Dict[str, pd.DataFrame], mappings_df, default_values: dict):
    logs = []

    # file_name -> [ [data_file_field_name, cudr_field_name], ... ]
    data_df = pd.DataFrame()

    data_preprocessor = DataPreprocessor()

    for file_name in data_dicts:
        file_mapping = mappings_df[mappings_df['file_name'] == file_name]
        current_data = data_dicts[file_name]

        for _, row in file_mapping.iterrows():
            data_file_field = row['data_file_field_names']
            cudr_field = row['cudr_field_names']

            if data_file_field not in current_data:
                raise logic.ValidationError([f'Cannot find field `{data_file_field}` in `{file_name}`'])
            else:
                data_df[cudr_field] = current_data[data_file_field]

            data_df['accessed_date'] = pd.Timestamp.today().strftime('%Y-%m-%d')

    data_preprocessor.clean_and_append_numbers(data_df, 'title')

    if 'title' in data_df.columns:
        data_df['name'] = data_df['title'].apply(data_preprocessor.clean_title)

    if 'tags' in data_df.columns:
        data_df['tags'] = data_df['tags'].apply(data_preprocessor.clean_tags)

    if 'geo_span' in data_df.columns:
        data_df['geo_span'] = data_df['geo_span'].apply(
            data_preprocessor.clean_geo_span)

    if 'time_span_start' in data_df.columns:
        data_df['time_span_start'] = data_df['time_span_start'].apply(
            data_preprocessor.clean_min_date)

    if 'time_span_end' in data_df.columns:
        data_df['time_span_end'] = data_df['time_span_end'].apply(
            data_preprocessor.clean_max_date)

    result_list = data_df.to_dict(orient='records')

    # if the key does not exist in the datafile, populate it with the default value
    for d in result_list:
        for key, value in default_values.items():
            if key not in d:
                d[key] = value

    # loading datasets into CKAN iteratively
    for i, data in enumerate(result_list):
        try:
            data['type'] = 'catalogue'

            # Create a new context for each catalogue entry creation
            context = cast(Context, {
                'model': model,
                'session': model.Session,
                'user': current_user.name,
                'auth_user_obj': current_user
            })
            created_package = toolkit.get_action("package_create")(context, data)
            logs.append(f'Catalogue entry created: {created_package["name"]}')

            # loading the associated resource for the metadata
            resource = {
                'package_id': created_package['id'],
                'url': data.get('url', ''),
                'name': data.get('title', ''),
                'description': data.get('description', ''),
                'format': data.get('format', '')
            }
            resource = toolkit.get_action("resource_create")(context, resource)
            logs.append(f'Dataset {resource["id"]} added to the Catalogue entry {created_package["name"]}')
        except logic.ValidationError as e:
            e.error_dict['Error when importing'] = [
                f'title="{data.get("title", "")}", index={i}']
            raise e

    return logs
