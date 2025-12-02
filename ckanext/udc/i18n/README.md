## Generating new base pot file `ckanext/udc/i18n/ckanext-udc.pot`
> see [CKAN Internationalization Documentation](https://docs.ckan.org/en/latest/extensions/translating-extensions.html#internationalizing-strings-in-extensions) for more details.
```shell
cd ckanext-udc
python setup.py extract_messages
```
This will create/update the `ckanext-udc.pot` file in the `ckanext/udc/i18n` directory.

## Updating French translation file
> If this is the first time creating the French translation file, run the `init_catalog` command instead of `update_catalog`.

After updating the base pot file, update the translation files (`.po` files) for each language.
```shell
cd ckanext-udc
python setup.py update_catalog --locale fr
```

## Compiling translation files after deploying changes
After updating the translation files, compile them into binary `.mo` files that CKAN can use.
```shell
cd ckanext-udc
python setup.py compile_catalog
ckan -c /etc/ckan/default/ckan.ini translation js
```