import { Paper, Box, InputLabel, FormControl, Button, Divider, Switch, TextField, Autocomplete, FormControlLabel, RadioGroup, Radio, CircularProgress } from '@mui/material';
import Grid from '@mui/material/Unstable_Grid2'; // Grid version 2
import CodeMirror from "@uiw/react-codemirror";
import { python } from '@codemirror/lang-python';
import { useMemo, useState } from 'react';
import { SaveOutlined, PlayArrowOutlined, DeleteForeverOutlined } from '@mui/icons-material';
import { useApi } from '../api/useApi';
import { CKANOrganization } from '../api/api';
import OrganizationMapper from './mapper/OrganizationMapper';

export interface ImportPanelProps {
  defaultConfig?: {
    uuid: string;
    name?: string;
    code?: string;
    notes?: string;
    owner_org?: string;
    stop_on_error?: boolean;
    other_config?: {
      org_import_mode?: string;
      base_api?: string;
      org_mapping?: { [k: string]: string };
      delete_previously_imported?: boolean;
    };
    cron_schedule?: string;
    platform?: string;
    created_at?: string;
    updated_at?: string;
  };
  onUpdate: (option?: string) => void;
  organizations: CKANOrganization[];
}

const supportedPlatform = [
  { id: "ckan", label: "CKAN" },
  { id: "socrata", label: "Socrata" },
]

export default function ImportPanel(props: ImportPanelProps) {
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
    other_config: props.defaultConfig?.other_config ?? {},
  });

  const [loading, setLoading] = useState({ save: false, saveAndRun: false, delete: false });

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

  const handleSwitchChangeDelete = (e: any) => {
    setImportConfig(initials => ({
      ...initials,
      other_config: {
        ...initials.other_config,
        delete_previously_imported: e.target.checked
      }
    }));
  }

  const handleSave = async () => {
    setLoading(prev => ({ ...prev, save: true }));
    try {
      await executeApiCall(() => api.updateImportConfig(importConfig));
      props.onUpdate();
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(prev => ({ ...prev, save: false }));
    }
  }

  const handleSaveAndRun = async () => {
    setLoading(prev => ({ ...prev, saveAndRun: true }));
    try {
      const { result } = await executeApiCall(() => api.updateImportConfig(importConfig));
      if (result?.id) {
        await executeApiCall(() => api.runImport(result.id))
        // show import status
        props.onUpdate('show-status');
      }

    } catch (e) {
      console.error(e)
    } finally {
      setLoading(prev => ({ ...prev, saveAndRun: false }));
    }
  }

  const handleDelete = async () => {
    setLoading(prev => ({ ...prev, delete: true }));
    try {
      if (importConfig.uuid)
        await executeApiCall(() => api.deleteImportConfig(importConfig.uuid!))
      props.onUpdate();
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(prev => ({ ...prev, delete: false }));
    }
  }


  const handleChangeOtherConfig = (name: string) => (value: any) => {
    setImportConfig(initials => ({
      ...initials,
      other_config: {
        ...initials.other_config,
        [name]: value?.target instanceof Object ? value.target.value : value
      }
    }));
  }

  const orgMappingComponent = useMemo(() => {
    console.log(importConfig.other_config)
    return <OrganizationMapper defaultValue={importConfig.other_config.org_mapping} externalBaseApi={importConfig.other_config.base_api!} onChange={handleChangeOtherConfig('org_mapping')} />
  }, [importConfig.other_config.base_api]);

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
            options={supportedPlatform}
            getOptionLabel={(option) => option.label}
            value={supportedPlatform.find(p => p.id === importConfig.platform) || null}
            onChange={handleChangePlatform}
            renderInput={(params) => <TextField {...params} label="Platform" />}
          />
        </Grid>
        {importConfig.platform === 'ckan' && (
          <>
            <Grid xs={12}>
              <TextField
                label="API URL"
                value={importConfig.other_config.base_api}
                onChange={handleChangeOtherConfig("base_api")}
                helperText="e.g. https://open.canada.ca/data/api/"
                fullWidth
              />
            </Grid>

            <Grid xs={12} sx={{ mt: 2 }}>
              <FormControl fullWidth variant="standard">
                <InputLabel shrink sx={{ fontSize: "22px", fontWeight: 600, mb: 10 }}>
                  Delete previously imported packages
                </InputLabel>
                <Box sx={{ pt: 3 }}>
                  <Switch color="primary" checked={importConfig.other_config.delete_previously_imported} onChange={handleSwitchChangeDelete} />
                </Box>
              </FormControl>

            </Grid>

            <Grid xs={12}>
              <FormControl component="fieldset">
                <RadioGroup
                  value={importConfig.other_config.org_import_mode}
                  onChange={handleChangeOtherConfig('org_import_mode')}
                >
                  <FormControlLabel
                    value="importToSpecifiedOrg"
                    control={<Radio />}
                    label="Import everything to a specified organization"
                  />
                  <FormControlLabel
                    value="importToOwnOrg"
                    control={<Radio />}
                    label="Import into its own organization, create if it does not exist, or map to an existing organization"
                  />
                </RadioGroup>
              </FormControl>
            </Grid>

            {importConfig.other_config.org_import_mode === "importToSpecifiedOrg" && (
              <Grid xs={12}>
                <Autocomplete
                  options={props.organizations}
                  getOptionLabel={(option) => option.display_name}
                  value={props.organizations.find(org => org.id === importConfig.owner_org) || null}
                  onChange={handleChangeOrganization}
                  renderInput={(params) => <TextField {...params} label="Organization" />}
                />
              </Grid>
            )}

            {importConfig.other_config.org_import_mode === "importToOwnOrg" && (
              <Grid xs={12}>
                {orgMappingComponent}
              </Grid>
            )}
          </>
        )}

        <Grid xs={12}>
          <TextField
            label="Cron Schedule"
            value={importConfig.cron_schedule}
            onChange={handleChange("cron_schedule")}
            placeholder="e.g. */10 * * * * for every 10 minutes"
            sx={{ mt: 1 }}
            fullWidth
            disabled
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
            <FormControl variant="standard" fullWidth sx={{ mt: 3 }}>
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
          <FormControl fullWidth variant="standard" disabled>
            <InputLabel shrink sx={{ fontSize: "22px", fontWeight: 600, mb: 10 }}>
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
          <Button
            variant="outlined"
            startIcon={loading.save ? <CircularProgress size={24} /> : <SaveOutlined />}
            sx={{ textTransform: "none" }}
            onClick={handleSave}
            disabled={loading.save}
          >
            {'Save'}
          </Button>
        </Grid>
        <Grid>
          <Button
            variant="outlined"
            color="success"
            startIcon={loading.saveAndRun ? <CircularProgress size={24} /> : <PlayArrowOutlined />}
            sx={{ textTransform: "none" }}
            onClick={handleSaveAndRun}
            disabled={loading.saveAndRun || loading.save}
          >
            {'Save and Run Import'}
          </Button>
        </Grid>
        {importConfig.uuid && <Grid>
          <Button
            variant="outlined"
            startIcon={loading.delete ? <CircularProgress size={24} /> : <DeleteForeverOutlined />}
            color="error"
            sx={{ textTransform: "none" }}
            onClick={handleDelete}
            disabled={loading.delete || loading.save || loading.saveAndRun}
          >
            {'Delete'}
          </Button>
        </Grid>}
      </Grid>
    </Paper>
  );
}

