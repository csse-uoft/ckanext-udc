import { Container, Typography } from '@mui/material';
import Grid from '@mui/material/Unstable_Grid2';
import { useEffect, useState } from 'react';
import { useApi } from '../api/useApi';
import { CKANOrganization, ImportConfig, ImportConfigListItem } from '../api/api';
import ImportPanel from './ImportPanel';
import ImportConfigList, { ImportListItem } from './components/ImportConfigList';

export default function ImportDashboard() {
  const { api, executeApiCall } = useApi();
  const [configs, setConfigs] = useState<ImportListItem[]>([]);
  const [selectedConfigId, setSelectedConfigId] = useState<string>('');
  const [organizations, setOrganizations] = useState<CKANOrganization[]>([]);
  const [selectedConfig, setSelectedConfig] = useState<ImportConfig | null>(null);

  const load = async (option?: string) => {
    // Get organizations
    const [organizations, importConfigs] = await Promise.all([
      executeApiCall(api.getOrganizations),
      executeApiCall(api.getImportConfigList),
    ]);
    setOrganizations(organizations);

    const items: ImportListItem[] = (importConfigs as ImportConfigListItem[])
      .filter((config) => !config.auto_arcgis)
      .map((config) => ({ id: config.id, name: config.name }));
    setConfigs(items);
    if (!selectedConfigId && items.length > 0) {
      setSelectedConfigId(items[0].id);
    }
  }
  const requestRefresh = () => {
    load();
  }

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    let active = true;
    if (!selectedConfigId) {
      setSelectedConfig(null);
      return;
    }
    executeApiCall(() => api.getImportConfig(selectedConfigId))
      .then((config) => {
        if (active) {
          setSelectedConfig(config);
        }
      })
      .catch(() => {
        if (active) {
          setSelectedConfig(null);
        }
      });
    return () => {
      active = false;
    };
  }, [api, executeApiCall, selectedConfigId]);

  return (
    <Container>
      <Typography variant="h5" paddingBottom={2}>Import</Typography>
      <Grid container spacing={2}>
        <Grid xs={12} md={4}>
          <ImportConfigList
            items={[{ id: 'new-import', name: 'New Import' }, ...configs]}
            selectedId={selectedConfigId || 'new-import'}
            onSelect={(id) => {
              setSelectedConfigId(id === 'new-import' ? '' : id);
            }}
            height={700}
          />
        </Grid>
        <Grid xs={12} md={8}>
          {selectedConfigId ? (
            <ImportPanel
              key={selectedConfigId}
              defaultConfig={selectedConfig ? { uuid: selectedConfigId, ...selectedConfig } : undefined}
              onUpdate={requestRefresh}
              organizations={organizations}
            />
          ) : (
            <ImportPanel onUpdate={requestRefresh} organizations={organizations} />
          )}
        </Grid>
      </Grid>
    </Container>
  );
}
