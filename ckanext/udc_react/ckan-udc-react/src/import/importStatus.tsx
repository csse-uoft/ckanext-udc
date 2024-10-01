import { Container, Card, CardContent, Alert, Typography, Box, IconButton, Button, FormControl, InputLabel, Select, MenuItem} from '@mui/material';
import Grid from '@mui/material/Unstable_Grid2'; // Grid version 2
import DynamicTabs, { IDynamicTab } from './tabs';

import CodeMirror from "@uiw/react-codemirror";
import { useEffect, useState } from 'react';
import { IImportConfig } from './import';
import DeleteIcon from '@mui/icons-material/Delete';
import { useApi } from '../api/useApi';
import { FinishedPackagesTable } from './realtime/FinishedPackagesTable';
import { FinishedPackage } from './realtime/types';


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
    finished: FinishedPackage[];
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
            Run At: {new Date(data.run_at).toLocaleString()}
          </Typography>
          <IconButton onClick={() => onDelete(data.id)} color="error" aria-label="delete">
            <DeleteIcon />
          </IconButton>
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
        

        <FinishedPackagesTable finishedPackages={data.other_data.finished} />
        
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
                {new Date(log.run_at).toLocaleString()}
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

  const [tabs, setTabs] = useState<IDynamicTab[]>([]);

  const load = async (option?: string) => {
    const importConfigs: IImportConfig = await executeApiCall(api.getImportConfigs);
    const newTabs = [];
    for (const [uuid, { code, name }] of Object.entries(importConfigs)) {
      newTabs.push({
        key: uuid, label: name, panel: <ImportLogsPanel uuid={uuid} defaultCode={code} defaultName={name} onUpdate={requestRefresh} />
      })
    }
    setTabs(newTabs);
  }
  const requestRefresh = () => {
    load();
  }

  useEffect(() => {
    load();
  }, []);


  if (tabs.length === 0)
    return "Loading..."

  return <Container>
    <Typography variant='h5' paddingBottom={2}>Import Status</Typography>

    <DynamicTabs tabs={tabs} />
  </Container>


}