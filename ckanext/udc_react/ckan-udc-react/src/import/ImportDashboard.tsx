import { Container } from '@mui/material';
import DynamicTabs, { IDynamicTab } from './tabs';
import { useEffect, useState } from 'react';
import { useApi } from '../api/useApi';
import { IImportConfig } from './types';
import ImportPanel from './ImportPanel';

export default function ImportDashboard() {
  const { api, executeApiCall } = useApi();
  const [tabs, setTabs] = useState<IDynamicTab[]>([]);

  const load = async (option?: string) => {
    // Get organizations
    const organizations = await executeApiCall(api.getOrganizations);

    const importConfigs: IImportConfig = await executeApiCall(api.getImportConfigs);
    const newTabs = [];
    for (const [uuid, config] of Object.entries(importConfigs)) {
      const { code, name } = config;
      newTabs.push({
        key: uuid, label: name, panel: <ImportPanel defaultConfig={{ uuid, ...config }} onUpdate={requestRefresh} organizations={organizations} />
      })
    }
    newTabs.push({ key: "new-import", label: "New Import", panel: <ImportPanel onUpdate={requestRefresh} organizations={organizations} /> });
    setTabs(newTabs);
  }
  const requestRefresh = () => {
    load();
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <Container>
      <DynamicTabs tabs={tabs} />
    </Container>
  );
}
