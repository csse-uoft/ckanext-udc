import { Container, Paper, Box, InputLabel, FormControl, Button, Divider, Switch, TextField, Autocomplete, FormControlLabel, FormGroup } from '@mui/material';
import Grid from '@mui/material/Unstable_Grid2'; // Grid version 2
import DynamicTabs, { IDynamicTab } from './tabs';
import CodeMirror from "@uiw/react-codemirror";
import { python } from '@codemirror/lang-python';
import { BootstrapTextField } from './inputs';
import { useEffect, useState } from 'react';
import { SaveOutlined, PlayArrowOutlined, DeleteForeverOutlined } from '@mui/icons-material';
import { useApi } from '../api/useApi';
import { CKANOrganization } from '../api/api';

export type IImportConfig = { uuid?: string, code: string, name: string }[];

export interface ImportPanelProps {
  defaultConfig?: {
    uuid: string;
    name?: string;
    code?: string;
    notes?: string;
    owner_org?: string;
    stop_on_error?: boolean;
    other_config?: object;
    cron_schedule?: string;
    platform?: string;
    created_at?: string;
    updated_at?: string;
  };
  onUpdate: (option?: string) => void;
  organizations: CKANOrganization[];
}

const supportedPlatform = [
  {id: "ckan", label: "CKAN"},
  {id: "socrata", label: "Socrata"},
]

function ImportPanel(props: ImportPanelProps) {
  const { api, executeApiCall } = useApi();

  const [importConfig, setImportConfig] = useState({
    uuid: props.defaultConfig?.uuid,
    name: props.defaultConfig?.name ?? "",
    code: props.defaultConfig?.code ?? "",
    notes: props.defaultConfig?.notes ?? "",
    owner_org: props.defaultConfig?.owner_org ?? "",
    stop_on_error: props.defaultConfig?.stop_on_error ?? false,
    cron_schedule: props.defaultConfig?.cron_schedule ?? "",
    platform: props.defaultConfig?.platform ?? "ckan",
  });

  const handleChange = (field: string) => (e: any) => {
    setImportConfig(initials => ({
      ...initials,
      [field]: e.target.value
    }));
  }

  const handleChangeCode = (code: string) => {
    setImportConfig(initials => ({
      ...initials,
      code,
    }));
  }

  const handleChangeOrganization = (e: any, value: CKANOrganization | null) => {
    setImportConfig(initials => ({
      ...initials,
      owner_org: value ? value.id : ""
    }));
  }

  const handleChangePlatform = (e: any, value: any) => {
    setImportConfig(initials => ({
      ...initials,
      platform: value ? value.id : ""
    }));
  }

  const handleSwitchChange = (e: any) => {
    setImportConfig(initials => ({
      ...initials,
      stop_on_error: e.target.checked
    }));
  }

  const handleSave = async () => {
    try {
      await executeApiCall(() => api.updateImportConfig(importConfig));
      props.onUpdate();
    } catch (e) {
      console.error(e)
    }
  }

  const handleSaveAndRun = async () => {
    try {
      const { result } = await executeApiCall(() => api.updateImportConfig(importConfig));
      if (result?.id) {
        await executeApiCall(() => api.runImport(result.id))
        // show import status
        props.onUpdate('show-status');
      }

    } catch (e) {
      console.error(e)
    }
  }

  const handleDelete = async () => {
    try {
      if (importConfig.uuid)
        await executeApiCall(() => api.deleteImportConfig(importConfig.uuid!))
      props.onUpdate();
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <Paper variant='outlined' sx={{ p: 3 }}>
      <Grid container spacing={2}>
        <Grid xs={8}>
          <TextField
            label="Import Name"
            value={importConfig.name}
            onChange={handleChange("name")}
            helperText={importConfig.uuid && 'UUID: ' + importConfig.uuid}
          />
        </Grid>
        <Grid xs={12}>
          <Autocomplete
            options={props.organizations}
            getOptionLabel={(option) => option.display_name}
            value={props.organizations.find(org => org.id === importConfig.owner_org) || null}
            onChange={handleChangeOrganization}
            renderInput={(params) => <TextField {...params} label="Organization" />}
          />
        </Grid>
        <Grid xs={12}>
          <Autocomplete
            options={supportedPlatform}
            getOptionLabel={(option) => option.label}
            value={supportedPlatform.find(p => p.id === importConfig.platform) || null}
            onChange={handleChangePlatform}
            renderInput={(params) => <TextField {...params} label="Platform" />}
          />
        </Grid>
        <Grid xs={12}>
          <TextField
            label="Cron Schedule"
            value={importConfig.cron_schedule}
            onChange={handleChange("cron_schedule")}
            placeholder="e.g. */10 * * * * for every 10 minutes"
            sx={{ mt: 1 }}
            fullWidth
          />

          <Grid xs={12}>
            <TextField
              label="Notes"
              value={importConfig.notes}
              onChange={handleChange("notes")}
              multiline
              rows={4}
              sx={{ mt: 3 }}
              fullWidth
            />
          </Grid>

          <Grid xs={12}>
            <FormControl variant="standard" fullWidth sx={{mt: 3}}>
              <InputLabel shrink sx={{ fontSize: "22px", fontWeight: 600 }}>
                Python code snippets
              </InputLabel>
              <Box sx={{ pt: 4, minHeight: 424 }}>
                <CodeMirror
                  value={importConfig.code}
                  minHeight="400px"
                  maxHeight='800px'
                  onChange={handleChangeCode}
                  extensions={[python()]}
                />
              </Box>
            </FormControl>
          </Grid>

        </Grid>

        <Grid xs={12} sx={{ mt: 2 }}>
          <FormControl fullWidth variant="standard">
            <InputLabel shrink sx={{ fontSize: "22px", fontWeight: 600,  mb: 10 }}>
              Stop on error
            </InputLabel>
            <Box sx={{ pt: 3 }}>
              <Switch color="primary" checked={importConfig.stop_on_error} onChange={handleSwitchChange} />
            </Box>
          </FormControl>

        </Grid>
        <Grid xs={12}>
          <Divider />
        </Grid>
        <Grid>
          <Button variant="outlined" startIcon={<SaveOutlined />} sx={{ textTransform: "none" }} onClick={handleSave}>
            Save
          </Button>
        </Grid>
        <Grid>
          <Button variant="outlined" color="success" startIcon={<PlayArrowOutlined />} sx={{ textTransform: "none" }} onClick={handleSaveAndRun}>
            Save and Run Import
          </Button>
        </Grid>
        {importConfig.uuid && <Grid>
          <Button variant="outlined" startIcon={<DeleteForeverOutlined />} color="error" sx={{ textTransform: "none" }} onClick={handleDelete}>
            Delete
          </Button>
        </Grid>}
      </Grid>
    </Paper>
  );
}

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
