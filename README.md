[![Tests](https://github.com/csse-uoft/ckanext-udc/workflows/Tests/badge.svg?branch=main)](https://github.com/csse-uoft/ckanext-udc/actions)

# ckanext-udc

## [Developer Manual](./DEV.md)
## Config Schema
```js
[   
    // The first level.
    {
        "title": "level 1 title",
        "name": "maturity_level_1",
        "fields": [
            {
                // Internal names, used in APIs. Special characters are not allowed.
                "name": "theme",

                // The Label of this field
                "label": "Domain / Topic",

                // The short description is under the field
                "short_description": "The theme.",

                // The long description is displayed when the cursor is hovered/clicked on the `quesion mark icon`
                "long_description": "The theme or topic of the package.",

                // The type of this field, default to "text".        
                // See "Supported field types" section for all supported types.
                "type": "text"
            },
            {
                // This clones the field that predefined in CKAN.
                // See "Supported CKAN Fields" section for all supported CKAN Fields
                "ckanField": "tags",

                // The short description is under the field
                "short_description": "The tags or keywords.",

                // The long description is displayed when the cursor is hovered/clicked on the `quesion mark icon`
                "long_description": "The tags or keywords of the package.",

            },
        ]
    },
    // The second level.
    {
        "title": "level 2 title",
        "name": "maturity_level_2",
        "fields": [
            {...}
        ]
    }
]
```

### Supported CKAN Fields
> Notes: short description and long description are not available for `title`, `license`, `organization_and_visibility` 
- `title` (*required): Title
- `description`: Description
- `tags`: Tags / Keywords
- `license_id`: License
- `organization_and_visibility` (*required): organization dropdown
- `source`: url to the source
- `version`: version number
- `author`: Author/Creator
- `author_email`
- `maintainer`
- `maintainer_email`
- `custom_fields`: Custom CKAN Fields, key/value pairs

### Supported field types
- `text`
- `date`
- `datetime`
- `time`
- `single_select`
   ```js
   {
       "name": "access_diff_version",
       "label": "Can different versions of the data be accessed?",
       "type": "single_select",
       // A list of available options.
       // The "value" must be a string.
       "options": [
           {"text": "N/A", "value": ""},
           {"text": "Yes", "value": "true"},
           {"text": "No", "value": "false"}
       ]
   }
   ```

## Requirements

If your extension works across different versions you can add the following table:

Compatibility with core CKAN versions:

| CKAN version    | Compatible?   |
| --------------- | ------------- |
| 2.6 and earlier | not tested    |
| 2.7             | not tested    |
| 2.8             | not tested    |
| 2.9             | not tested    |
| 2.10.X          | yes           |
| 2.11.X          | yes           |

Suggested values:

* "yes"
* "not tested" - I can't think of a reason why it wouldn't work
* "not yet" - there is an intention to get it working
* "no"


## Installation

**TODO:** Add any additional install steps to the list below.
   For example installing any non-Python dependencies or adding any required
   config settings.

To install ckanext-udc:

1. Activate your CKAN virtual environment, for example:

    ```shell
    . /usr/lib/ckan/default/bin/activate
    ```

2. Clone the source and install it on the virtualenv

    ```shell
    cd /usr/lib/ckan/default/src/
    git clone https://github.com/csse-uoft/ckanext-udc.git
    cd ckanext-udc
    pip install -e .
    pip install -r requirements.txt
    ```

3. Add `udc` to the `ckan.plugins` setting in your CKAN
   config file (by default the config file is located at
   `/etc/ckan/default/ckan.ini`).

4. Init DB
     ```shell
     # Use your own path to the ckan.ini
     ckan -c /etc/ckan/default/ckan.ini udc initdb
     ```

5. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu:

     ```shell
     sudo supervisorctl reload
     ```


## Config settings

None at present


## Developer installation

To install ckanext-udc for development, activate your CKAN virtualenv and
do:

```shell
git clone https://github.com/csse-uoft/ckanext-udc.git
cd ckanext-udc
python setup.py develop
pip install -r dev-requirements.txt
```


## Tests

To run the tests, do:

    pytest --ckan-ini=test.ini


## Releasing a new version of ckanext-udc

If ckanext-udc should be available on PyPI you can follow these steps to publish a new version:

1. Update the version number in the `setup.py` file. See [PEP 440](http://legacy.python.org/dev/peps/pep-0440/#public-version-identifiers) for how to choose version numbers.

2. Make sure you have the latest version of necessary packages:

       pip install --upgrade setuptools wheel twine

3. Create a source and binary distributions of the new version:

       python setup.py sdist bdist_wheel && twine check dist/*

   Fix any errors you get.

4. Upload the source distribution to PyPI:

       twine upload dist/*

5. Commit any outstanding changes:

       git commit -a
       git push

6. Tag the new release of the project on GitHub with the version number from
   the `setup.py` file. For example if the version number in `setup.py` is
   0.0.1 then do:

       git tag 0.0.1
       git push --tags

## License

[AGPL](https://www.gnu.org/licenses/agpl-3.0.en.html)
