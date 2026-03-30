### Usage

Move all datasets to catalogues
```
source /usr/lib/ckan/default/bin/activate
ckan -c /etc/ckan/default/ckan.ini udc move-to-catalogues
ckan -c /etc/ckan/default/ckan.ini search-index rebuild
```

Check malformed number fields on datasets/catalogues
```
source /usr/lib/ckan/default/bin/activate
ckan -c /etc/ckan/default/ckan.ini udc migrate-number-fields
```

Normalize fixable localized number values such as {"en": "351"}
```
source /usr/lib/ckan/default/bin/activate
ckan -c /etc/ckan/default/ckan.ini udc migrate-number-fields --fix
ckan -c /etc/ckan/default/ckan.ini search-index rebuild
```
