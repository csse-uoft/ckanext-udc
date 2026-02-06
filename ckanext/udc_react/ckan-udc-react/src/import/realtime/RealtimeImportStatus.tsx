import { Container, Typography } from '@mui/material';
import { useEffect, useState } from 'react';
import { useApi } from '../../api/useApi';
import { RealtimeImportPanel } from './RealtimeImportPanel';
import Grid from '@mui/material/Unstable_Grid2';
import ImportConfigList, { ImportListItem } from '../components/ImportConfigList';

export function RealtimeImportStatus() {
  const { api, executeApiCall } = useApi();
  const [configs, setConfigs] = useState<ImportListItem[]>([]);
  const [selectedConfigId, setSelectedConfigId] = useState<string>('');

  const load = async (preferredId?: string) => {
    const importConfigs = await executeApiCall(api.getImportConfigList);
    const items: ImportListItem[] = (importConfigs as Array<{ id: string; name: string }>).map((config) => ({
      id: config.id,
      name: config.name,
    }));
    setConfigs(items);
    const fallbackId = items[0]?.id ?? '';
    const available = new Set(items.map((item) => item.id));
    setSelectedConfigId((current) => {
      const candidate = preferredId || current;
      if (candidate && available.has(candidate)) {
        return candidate;
      }
      return fallbackId;
    });
  };

  const requestRefresh = () => {
    load();
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const key = params.get('config') || undefined;
    load(key || undefined);
  }, []);

  return (
    <Container>
      <Typography variant='h5' paddingBottom={2}>Realtime Import Status</Typography>
      <Grid container spacing={2}>
        <Grid xs={12} md={4}>
          <ImportConfigList
            items={configs}
            selectedId={selectedConfigId}
            onSelect={setSelectedConfigId}
            height={700}
          />
        </Grid>
        <Grid xs={12} md={8}>
          {selectedConfigId ? (
            <RealtimeImportPanel
              key={selectedConfigId}
              uuid={selectedConfigId}
              defaultCode=""
              defaultName=""
              onUpdate={requestRefresh}
            />
          ) : (
            <Typography variant="body2">Select an import to view realtime status.</Typography>
          )}
        </Grid>
      </Grid>
    </Container>
  );
}
