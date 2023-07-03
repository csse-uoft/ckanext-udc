### Usage

Move all datasets to catalogues
```
source /usr/lib/ckan/default/bin/activate
ckan -c /etc/ckan/default/ckan.ini udc move-to-catalogues
ckan -c /etc/ckan/default/ckan.ini search-index rebuild
```
