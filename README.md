[![Tests](https://github.com/csse-uoft/ckanext-udc/workflows/Tests/badge.svg?branch=main)](https://github.com/csse-uoft/ckanext-udc/actions)

# ckanext-udc

## [Developer Manual](./DEV.md)
## [Testing Instructions](./TESTING.md)
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
> Notes: If `type` is not provided, it will default to `text`.
- `text`
- `number`
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

<!-- ### Filter Types
Filter Types Available:
- `fulltext` Full text search
- `or` OR filter
- `and` AND filter
- `date_range` Date range filter
- `time_range` Time range filter
- `number_range` Number range filter

Default Filter Types based on field `type`:
- `text` - Default to `or` filter
- `single_select` - Default to `or` filter
- `multi_select` - Default to `or` filter
- `date` - Default to `date_range` filter
- `datetime` - Default to `date_range` filter
- `time` - Default to `time_range` filter
- `number` - Default to `number_range` filter -->


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
   
To Install NodeJS 20:
```shell
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
# Reopen terminal or following the guide in the output to add 'nvm'

# Install NodeJS 20
nvm install 20
```

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

3. Add `udc udc_theme udc_import udc_import_other_portals udc_react` to the `ckan.plugins` setting in your CKAN
   config file (by default the config file is located at
   `/etc/ckan/default/ckan.ini`).
   > If you want to use the `activity` plugin, put it to the top (order matters).

    Adjust `ckan.jobs.timeout` to 36000 (10 hours)

4. Compiling translation files
    ```shell
    cd /usr/lib/ckan/default/src/ckanext-udc
    python setup.py compile_catalog
    ckan -c /etc/ckan/default/ckan.ini translation js
    ```

5. Install UDC-React Dependencies & Build
   ```
   cd /usr/lib/ckan/default/src/ckanext-udc/ckanext/udc_react/ckan-udc-react
   npm install
   npm run build
   ```

6. Init DB
     ```shell
     # Use your own path to the ckan.ini
     ckan -c /etc/ckan/default/ckan.ini udc initdb
     ```

7. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu:

     ```shell
     sudo supervisorctl reload
     ```

## Configure deployment server to support websocket connection and use Gevent for multi-tasking

1. Reinstall uwsgi with SSL support
    ```shell
    sudo apt-get install libssl-dev

    source /usr/lib/ckan/default/bin/activate

    # Uninstall previous version of `uwsgi` if exists
    pip uninstall uwsgi

    ## Manually build uwsgi with SSL support
    # set necessary lib paths
    export CFLAGS="-I/usr/include/openssl"
    # aarch64-linux-gnu folder used for ARM architecture and may be different for your env
    # use [apt-file list libssl-dev] to check lib folders (apt-file should be additionally installed)
    export LDFLAGS="-L/usr/lib/aarch64-linux-gnu"
    # activate SSL support
    export UWSGI_PROFILE_OVERRIDE=ssl=true
    # build uwsgi using pip (--no-use-wheel deprecated so used --no-binary instead)
    # this command will install 2.0.20 version. Version may be changed or removed. It is not mandatory
    pip install -I --no-binary=:all: --no-cache-dir uwsgi

    # Check SSL support
    uwsgi --help | grep https
    ```

2. Add to `/etc/ckan/default/ckan-uwsgi.ini`
    > Remove `enable-threads` and `threads` if exists, threading is not compitable with `gevent`.
    ```ini
    gevent          =  100 # number of coroutine
    http-websockets = true
    gevent-monkey-patch = true
    ```

3. Update nginx config `sudo nano /etc/nginx/sites-enabled/ckan`
    
    Add the following after `location / {...}`
    ```nginx
    location /socket.io/ {
        proxy_pass http://127.0.0.1:8080/socket.io/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }
    ```
4. Copy `wsgi.py` to apply monkey patching
    ```shell
    cp /usr/lib/ckan/default/src/ckanext-udc/ckanext/udc/wsgi.py /etc/ckan/default/wsgi.py
    ```

## Config settings

None at present


### Run as a developer

- CKAN main procress
    ```shell
    source /usr/lib/ckan/default/bin/activate
    VITE_ORIGIN=http://<your-server-ip>:5173 WERKZEUG_DEBUG_PIN=223344 uwsgi --http :5000 --gevent 1000 --http-websockets --master --wsgi-file /etc/ckan/default/wsgi.py --callable application --module wsgi:application --py-autoreload=1
    ```
- React Frontend
    ```shell
    cd /usr/lib/ckan/default/src/ckanext-udc/ckanext/udc_react/ckan-udc-react/
    npm run dev -- --host 0.0.0.0
    ```
- CKAN worker process
    ```shell
    source /usr/lib/ckan/default/bin/activate
    WERKZEUG_DEBUG_PIN=223344 ckan -c /etc/ckan/default/ckan.ini jobs worker
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
