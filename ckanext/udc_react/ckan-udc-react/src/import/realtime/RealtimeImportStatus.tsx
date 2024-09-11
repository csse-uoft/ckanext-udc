import { Container, Typography } from '@mui/material';
import { useEffect, useState } from 'react';
import { useApi } from '../../api/useApi';
import DynamicTabs, { IDynamicTab } from '../tabs';
import { RealtimeImportPanel } from './RealtimeImportPanel';

export function RealtimeImportStatus() {
  const { api, executeApiCall } = useApi();
  const [tabs, setTabs] = useState<IDynamicTab[]>([]);

  const load = async (option?: string) => {
    const importConfigs = await executeApiCall(api.getImportConfigs) as Record<string, { code: string, name: string }>;
    const newTabs = [];
    for (const [uuid, { code, name }] of Object.entries(importConfigs)) {
      newTabs.push({
        key: uuid,
        label: name,
        panel: <RealtimeImportPanel uuid={uuid} defaultCode={code} defaultName={name} onUpdate={requestRefresh} />
      });
    }
    setTabs(newTabs);
  };

  const requestRefresh = () => {
    load();
  };

  useEffect(() => {
    load();
  }, []);

  if (tabs.length === 0) return "Loading...";

  return (
    <Container>
      <Typography variant='h5' paddingBottom={2}>Realtime Import Status</Typography>
      <DynamicTabs tabs={tabs} />
    </Container>
  );
}
