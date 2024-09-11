import { Container, Card, CardContent, Alert, Typography, Box, IconButton, } from '@mui/material';
import Grid from '@mui/material/Unstable_Grid2'; // Grid version 2
import DynamicTabs, { IDynamicTab } from './tabs';

import CodeMirror from "@uiw/react-codemirror";
import { useEffect, useState } from 'react';
import { IImportConfig } from './import';
import DeleteIcon from '@mui/icons-material/Delete';
import { useApi } from '../api/useApi';


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
  other_data: string | null;
  run_at: string;
  run_by: string;
}

interface LogPanelProps {
  data: LogData;
  onDelete: (id: string) => void;
}

const LogPanel: React.FC<LogPanelProps> = ({ data, onDelete }) => {
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
        <Typography color="text.secondary">
          Logs:
        </Typography>
        <CodeMirror
          value={data.logs || ''}
          // @ts-ignore
          options={{
            theme: 'material',
            lineNumbers: true,
            readOnly: true,
          }}
        />
      </CardContent>
    </Card>
  );
};


function ImportLogsPanel(props: ImportPanelProps) {
  const {api, executeApiCall} = useApi();
  const [importLogs, setImportLogs] = useState([]);

  useEffect(() => {
    executeApiCall(() => api.getImportLogsByConfigId(props.uuid)).then((logs: any) => {
      setImportLogs(logs);
      console.log(logs)
    })

  }, [props.uuid]);

  const handleDeleteOne = async (id: string) => {
    await executeApiCall(() => api.deleteImportLog(id));
    setImportLogs(logs => {
      logs.splice(logs.findIndex((log: LogData) => log.id === id), 1)
      return [...logs]
    })
  }

  return (
    <Grid container spacing={2}>
      {importLogs.map((data: LogData) => (
        <Grid xs={12} key={data.id}>
          <LogPanel data={data} onDelete={handleDeleteOne}/>
        </Grid>
      ))}
    </Grid>
  )
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