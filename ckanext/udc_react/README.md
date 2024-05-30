### Start Vito Dev Server
```
cd ckanext-udc/ckanext/udc_react/ckan-udc-react
npm run start
```

### Start CKAN Dev Server
```
VITE_ORIGIN=http://<your-vite-server-host>:5173 ckan -c /etc/ckan/default/ckan.ini run
```

### Create react production build
```
cd ckanext-udc/ckanext/udc_react/ckan-udc-react
npm run build
```