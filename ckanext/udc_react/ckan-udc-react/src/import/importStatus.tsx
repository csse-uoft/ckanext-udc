import { Container, Card, CardContent, Alert, Typography, Box, IconButton, Button, FormControl, InputLabel, Select, MenuItem, Tooltip } from '@mui/material';
import Grid from '@mui/material/Unstable_Grid2'; // Grid version 2

import { useEffect, useState } from 'react';
import { ImportConfigListItem } from '../api/api';
import DeleteIcon from '@mui/icons-material/Delete';
import { useApi } from '../api/useApi';
import { FinishedPackagesTable } from './realtime/FinishedPackagesTable';
import { FinishedPackage } from './realtime/types';
import ImportConfigList, { ImportListItem } from './components/ImportConfigList';
import { formatLocalTimestamp } from './utils/time';


export interface ImportPanelProps {
  uuid: string;
  defaultName?: string;
  defaultCode?: string;
  onUpdate: (option?: string) => void
}

interface LogData {
  has_error: boolean;
  has_warning: boolean;
  id: string;
  import_config_id: string;
  logs: string;
  other_data: {
    finished?: FinishedPackage[];
  };
  run_at: string;
  run_by: string;
}

interface LogPanelProps {
  data: LogData;
  onDelete: (id: string) => void;
}

const LogPanel: React.FC<LogPanelProps> = ({ data, onDelete }) => {
  const handleDownloadLogs = () => {
    const element = document.createElement('a');
    const file = new Blob([data.logs], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = `logs_${data.id}.txt`;
    document.body.appendChild(element); // Required for this to work in FireFox
    element.click();
  };

  return (
    <Card variant="outlined" sx={{ margin: '20px auto' }}>
      <CardContent>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Typography variant="h5" component="div">
            Run At: {formatLocalTimestamp(data.run_at)}
          </Typography>
          <Tooltip title="Delete log">
            <IconButton onClick={() => onDelete(data.id)} color="error" aria-label="delete">
              <DeleteIcon />
            </IconButton>
          </Tooltip>
        </Box>
        {data.has_error && (
          <Alert severity="error" sx={{ mt: 2, mb: 2 }}>
            Error: An error occurred during the process.
          </Alert>
        )}
        {data.has_warning && (
          <Alert severity="warning" sx={{ mt: 2, mb: 2 }}>
            Warning: There is a warning related to the process.
          </Alert>
        )}
        <Typography variant="body2" color="text.secondary">
          ID: {data.id}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Import Config ID: {data.import_config_id}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Run By: {data.run_by}
        </Typography>
        <Button variant="contained" color="primary" onClick={handleDownloadLogs} sx={{ mt: 2 }}>
          Download Logs
        </Button>
        

        <FinishedPackagesTable finishedPackages={data.other_data?.finished || []} />
        
      </CardContent>
    </Card>
  );
};


function ImportLogsPanel(props: ImportPanelProps) {
  const { api, executeApiCall } = useApi();
  const [importLogs, setImportLogs] = useState<LogData[]>([]);
  const [selectedLogId, setSelectedLogId] = useState<string>('');

  useEffect(() => {
    executeApiCall(() => api.getImportLogsByConfigId(props.uuid)).then((logs: LogData[]) => {
      setImportLogs(logs);
      if (logs.length > 0) {
        setSelectedLogId(logs[0].id); // Set the first log as the default selected log
      }
      console.log(logs);
    });
  }, [props.uuid]);

  const handleDeleteOne = async (id: string) => {
    await executeApiCall(() => api.deleteImportLog(id));
    setImportLogs(logs => {
      logs.splice(logs.findIndex((log: LogData) => log.id === id), 1);
      return [...logs];
    });
    if (selectedLogId === id) {
      setSelectedLogId(importLogs.length > 0 ? importLogs[0].id : '');
    }
  };

  const handleLogChange = (event: any) => {
    setSelectedLogId(event.target.value as string);
  };

  const selectedLog = importLogs.find(log => log.id === selectedLogId);

  return (
    <Grid container spacing={2}>
      <Grid xs={12}>
        <FormControl fullWidth >
          <InputLabel id="select-log-label">Select Import Log</InputLabel>
          <Select
            label="Select Import Log"
            labelId="select-log-label"
            value={selectedLogId}
            onChange={handleLogChange}
          >
            {importLogs.map((log: LogData) => (
              <MenuItem key={log.id} value={log.id}>
                {formatLocalTimestamp(log.run_at)}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Grid>
      {selectedLog && (
        <Grid xs={12}>
          <LogPanel data={selectedLog} onDelete={handleDeleteOne} />
        </Grid>
      )}
    </Grid>
  );
}


export function ImportStatus() {
  const {api, executeApiCall} = useApi();

  const [configs, setConfigs] = useState<ImportListItem[]>([]);
  const [selectedConfigId, setSelectedConfigId] = useState<string>('');
  const [requestedConfigId, setRequestedConfigId] = useState<string>('');

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const configId = params.get('configId') || '';
    if (configId) {
      setRequestedConfigId(configId);
      setSelectedConfigId(configId);
    }
  }, []);

  useEffect(() => {
    if (!requestedConfigId || configs.length === 0) {
      return;
    }
    const hasRequested = configs.some((item) => item.id === requestedConfigId);
    if (hasRequested && selectedConfigId !== requestedConfigId) {
      setSelectedConfigId(requestedConfigId);
    }
  }, [configs, requestedConfigId, selectedConfigId]);

  const load = async (option?: string) => {
    const importConfigs = await executeApiCall(api.getImportConfigList);
    const items: ImportListItem[] = (importConfigs as ImportConfigListItem[]).map((config) => {
      const updated = config.updated_at ? formatLocalTimestamp(config.updated_at) : '';
      return { id: config.id, name: config.name, subtitle: updated ? `Updated: ${updated}` : undefined };
    });
    setConfigs(items);
    if (requestedConfigId) {
      const hasRequested = items.some((item) => item.id === requestedConfigId);
      if (hasRequested) {
        setSelectedConfigId(requestedConfigId);
        return;
      }
    }
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

  if (configs.length === 0) return "Loading...";

  return (
    <Container>
      <Typography variant='h5' paddingBottom={2}>Import Status</Typography>
      <Grid container spacing={2}>
        <Grid xs={12} md={4}>
          <ImportConfigList
            items={configs}
            selectedId={selectedConfigId}
            onSelect={(id) => {
              setSelectedConfigId(id);
              const params = new URLSearchParams(window.location.search);
              if (id) {
                params.set("configId", id);
              } else {
                params.delete("configId");
              }
              const query = params.toString();
              const nextUrl = query ? `${window.location.pathname}?${query}` : window.location.pathname;
              window.history.replaceState(null, "", nextUrl);
            }}
            height={700}
          />
        </Grid>
        <Grid xs={12} md={8}>
          {selectedConfigId ? (
            <ImportLogsPanel
              key={selectedConfigId}
              uuid={selectedConfigId}
              defaultCode=""
              defaultName=""
              onUpdate={requestRefresh}
            />
          ) : (
            <Typography variant="body2">Select an import to view status.</Typography>
          )}
        </Grid>
      </Grid>
    </Container>
  );


}
