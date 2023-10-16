from __future__ import annotations

from ckan.types import Context
import logging
import os
import io
import zipfile
import uuid
import json
import pandas as pd
from typing import Any, cast

from urllib.parse import urljoin
from dateutil.parser import parse as parse_date

import ckan.lib.helpers as h
import ckan.logic as logic
import ckan.plugins as p
import ckan.lib.uploader as uploader
from ckan.common import config
from .utils import read_csv
from .import_data import load_data_to_ckan


log = logging.getLogger(__name__)


def udc_import_submit(context: Context, data_dict: dict[str, Any]):

    p.toolkit.check_access('udc_import_submit', context, data_dict)

    print(context, data_dict)

    # Save the upload
    upload = uploader.get_resource_uploader(data_dict)
    directory = os.path.join(uploader.get_storage_path(), 'udc_import', str(uuid.uuid4()))
    tmp_filename = upload.filename
    tmp_filepath = os.path.join(directory, tmp_filename)
    os.makedirs(directory, exist_ok=True)

    with open(tmp_filepath, 'wb+') as output_file:
        assert upload.upload_file
        try:
            uploader._copy_file(upload.upload_file, output_file, 100) # max 100MB
        except logic.ValidationError:
            os.remove(tmp_filepath)
            raise
        finally:
            upload.upload_file.close()

    try:
        filename2data = {} # data file filename -> data df
        # Unzip
        with zipfile.ZipFile(tmp_filepath, 'r') as zip_ref:
            try:
                with zip_ref.open('mapping.csv') as f:
                    mappings_df = pd.read_csv(f)
            except:
                raise logic.ValidationError("Missing `mapping.csv`")
            
            try:
                with zip_ref.open('default.json') as f:
                    default_values = json.load(f)
            except:
                raise logic.ValidationError("Missing `default.json`")
            
            try:
                with zip_ref.open('data_files.txt') as f:
                    data_file_names = [line.decode('UTF-8').strip() for line in f.readlines()]
            except:
                raise logic.ValidationError("Missing `data_files.txt`")

            for data_file_name in data_file_names:
                with zip_ref.open(data_file_name) as f:
                    filename2data[data_file_name] = pd.read_csv(f)
            
        # Import
        logs = load_data_to_ckan(filename2data, mappings_df, default_values)

        os.remove(tmp_filepath)
        return logs

    except:
        # Remove the upload
        os.remove(tmp_filepath)
        raise
        


def check_permission(context: Context, data_dict: dict[str, Any]):
    p.toolkit.check_access('udc_import_view', context, data_dict)
