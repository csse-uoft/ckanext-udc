import { Paper, Box, InputLabel, FormControl, Button, Divider, Switch, TextField, Autocomplete, FormControlLabel, RadioGroup, Radio, CircularProgress, Select, MenuItem, FormHelperText } from '@mui/material';
import Grid from '@mui/material/Unstable_Grid2'; // Grid version 2
import CodeMirror from "@uiw/react-codemirror";
import { python } from '@codemirror/lang-python';
import { useEffect, useMemo, useState } from 'react';
import { SaveOutlined, PlayArrowOutlined, DeleteForeverOutlined } from '@mui/icons-material';
import { useApi } from '../api/useApi';
import { CKANOrganization, ImportLanguageOptions } from '../api/api';
import CronScheduleEditor from './components/CronScheduleEditor';
import OrganizationMapper from './mapper/OrganizationMapper';
import { REACT_PATH } from '../constants';
import { buildCron, CustomCronField, defaultCustomCron, getCronSummary, normalizeCronSelection, parseCron, resolveCronPreset } from './utils/cron';

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
      language?: string;
      source_last_updated_cron_schedule?: string | null;
    };
    cron_schedule?: string;
    platform?: string;
    created_at?: string | null;
    updated_at?: string | null;
  };
  onUpdate: (option?: string) => void;
  organizations: CKANOrganization[];
  globalArcgisRefreshCron?: string | null;
}

const supportedPlatform = [
  { id: "ckan", label: "CKAN" },
  { id: "arcgis", label: "ArcGIS Hub" },
  { id: "socrata", label: "Socrata" },
]

const cronPresets = [
  { id: "none", label: "No schedule", cron: "" },
  { id: "daily_2am", label: "Daily at 2:00 AM", cron: "0 2 * * *" },
  { id: "weekly_monday_2am", label: "Weekly on Monday at 2:00 AM", cron: "0 2 * * 1" },
  { id: "monthly_first_2am", label: "Monthly on the 1st at 2:00 AM", cron: "0 2 1 * *" },
  { id: "custom", label: "Custom schedule", cron: "" },
];

const refreshCronPresets = [
  { id: "inherit", label: "Inherit global/default", cron: "" },
  { id: "hourly_15", label: "Every hour at minute 15", cron: "15 * * * *" },
  { id: "daily_2am", label: "Daily at 2:00 AM", cron: "0 2 * * *" },
  { id: "daily_6am", label: "Daily at 6:00 AM", cron: "0 6 * * *" },
  { id: "weekdays_6am", label: "Weekdays at 6:00 AM", cron: "0 6 * * 1,2,3,4,5" },
  { id: "custom", label: "Custom schedule", cron: "" },
];

const getRefreshCronSummary = (cron: string, customCron: typeof defaultCustomCron, inheritedCron?: string | null) => {
  if (!cron) {
    if (inheritedCron) {
      return `Inherits the global update-check schedule: ${inheritedCron}. This schedule runs the ArcGIS import and only updates datasets whose upstream source_last_updated changed.`;
    }
    return "No per-config override. This config will only run on schedule if a global update-check schedule is configured. When it runs, unchanged datasets are skipped based on source_last_updated.";
  }
  return `${getCronSummary(cron, customCron)} The run checks upstream source_last_updated and skips datasets that have not changed.`;
};

export default function ImportPanel(props: ImportPanelProps) {
  const { api, executeApiCall } = useApi();

  const buildImportConfig = (config?: ImportPanelProps["defaultConfig"]) => ({
    uuid: config?.uuid,
    name: config?.name ?? "",
    code: config?.code ?? "",
    notes: config?.notes ?? "",
    owner_org: config?.owner_org ?? "",
    stop_on_error: config?.stop_on_error ?? false,
    cron_schedule: config?.cron_schedule ?? "",
    platform: config?.platform ?? "ckan",
    other_config: config?.other_config ?? {},
  });

  const [importConfig, setImportConfig] = useState(() => buildImportConfig(props.defaultConfig));
  const [languageOptions, setLanguageOptions] = useState<ImportLanguageOptions | null>(null);

  const [loading, setLoading] = useState({ save: false, saveAndRun: false, delete: false });
  const [cronPreset, setCronPreset] = useState(() => resolveCronPreset(importConfig.cron_schedule, cronPresets));
  const [customCron, setCustomCron] = useState(() => parseCron(importConfig.cron_schedule));
  const [refreshCronPreset, setRefreshCronPreset] = useState(() =>
    resolveCronPreset(importConfig.other_config.source_last_updated_cron_schedule || "", refreshCronPresets)
  );
  const [refreshCustomCron, setRefreshCustomCron] = useState(() =>
    parseCron(importConfig.other_config.source_last_updated_cron_schedule || "")
  );
  const [languageLoading, setLanguageLoading] = useState(false);

  useEffect(() => {
    setImportConfig(buildImportConfig(props.defaultConfig));
  }, [props.defaultConfig?.uuid]);

  useEffect(() => {
    const currentCron = importConfig.other_config.source_last_updated_cron_schedule || "";
    const preset = resolveCronPreset(currentCron, refreshCronPresets);
    setRefreshCronPreset(preset);
    setRefreshCustomCron(parseCron(currentCron));
  }, [importConfig.other_config.source_last_updated_cron_schedule]);

  useEffect(() => {
    const preset = resolveCronPreset(importConfig.cron_schedule, cronPresets);
    setCronPreset(preset);
    if (preset === "custom") {
      setCustomCron(parseCron(importConfig.cron_schedule));
    }
  }, [importConfig.cron_schedule]);

  useEffect(() => {
    let active = true;
    setLanguageLoading(true);
    executeApiCall(api.getImportLanguageOptions)
      .then((result) => {
        if (active) {
          setLanguageOptions(result);
        }
      })
      .catch(() => {
        if (active) {
          setLanguageOptions(null);
        }
      })
      .finally(() => {
        if (active) {
          setLanguageLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [api, executeApiCall]);

  const getCodePlaceholder = () => {
    if (importConfig.platform === 'arcgis') {
      return `# Example: Ontario GeoHub or Manitoba GeoPortal Import
from ckanext.udc_import_other_portals.logic.arcgis_based.ontario_geohub import OntarioGeoHubImport
# from ckanext.udc_import_other_portals.logic.arcgis_based.manitoba_geoportal import ManitobaGeoPortalImport

class MyArcGISImport(OntarioGeoHubImport):
    def iterate_imports(self):
        """Filter datasets before import"""
        for dataset in self.all_datasets:
            attributes = dataset.get('attributes', {})
            # Only import public datasets
            if attributes.get('access') == 'public':
                yield dataset
    
    def map_to_cudc_package(self, src: dict, target: dict):
        """Customize the mapping if needed"""
        # Call parent implementation
        target = super().map_to_cudc_package(src, target)
        
        # Add custom mappings here
        # attributes = src.get('attributes', {})
        # target['custom_field'] = attributes.get('some_field')
        
        return target`;
    } else if (importConfig.platform === 'ckan') {
      return `# Example: CKAN Import
from ckanext.udc_import_other_portals.logic.ckan_based.base import CKANBasedImport

class MyImport(CKANBasedImport):
    def map_to_cudc_package(self, src: dict, target: dict):
        """Map source package to CUDC package"""
        # Basic mapping
        target["id"] = src.get("id", "")
        target["name"] = src.get("name", "")
        target["title"] = src.get("title", "")
        target["notes"] = src.get("notes", "")
        
        # Add more custom mappings as needed
        return target`;
    }
    return '';
  };

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
        const targetUrl = `/${REACT_PATH}/realtime-status?config=${result.id}`;
        window.location.assign(targetUrl);
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

  const handleChangeCronPreset = (value: string) => {
    setCronPreset(value);
    if (value === "custom") {
      const parsed = parseCron(importConfig.cron_schedule);
      setCustomCron(parsed);
      if (importConfig.cron_schedule) {
        setImportConfig(initials => ({
          ...initials,
          cron_schedule: buildCron(parsed),
        }));
      }
      return;
    }
    const selectedPreset = cronPresets.find((preset) => preset.id === value);
    setImportConfig(initials => ({
      ...initials,
      cron_schedule: selectedPreset ? selectedPreset.cron : "",
    }));
  };

  const handleChangeCustomCron = (field: CustomCronField, value: string[]) => {
    const normalized = normalizeCronSelection(value);
    const next = {
      ...customCron,
      [field]: normalized,
    };
    setCustomCron(next);
    setImportConfig(initials => ({
      ...initials,
      cron_schedule: buildCron(next),
    }));
  };

  const handleChangeRefreshCronPreset = (value: string) => {
    setRefreshCronPreset(value);
    if (value === "custom") {
      const parsed = parseCron(importConfig.other_config.source_last_updated_cron_schedule || "");
      setRefreshCustomCron(parsed);
      if (importConfig.other_config.source_last_updated_cron_schedule) {
        setImportConfig((initials) => ({
          ...initials,
          other_config: {
            ...initials.other_config,
            source_last_updated_cron_schedule: buildCron(parsed),
          },
        }));
      }
      return;
    }
    const selectedPreset = refreshCronPresets.find((preset) => preset.id === value);
    setImportConfig((initials) => ({
      ...initials,
      other_config: {
        ...initials.other_config,
        source_last_updated_cron_schedule: selectedPreset ? selectedPreset.cron : "",
      },
    }));
  };

  const handleChangeRefreshCustomCron = (field: CustomCronField, value: string[]) => {
    const normalized = normalizeCronSelection(value);
    const next = {
      ...refreshCustomCron,
      [field]: normalized,
    };
    setRefreshCustomCron(next);
    setImportConfig((initials) => ({
      ...initials,
      other_config: {
        ...initials.other_config,
        source_last_updated_cron_schedule: buildCron(next),
      },
    }));
  };

  const orgMappingComponent = useMemo(() => {
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
        {(importConfig.platform === 'ckan' || importConfig.platform === 'arcgis') && (
          <>
            <Grid xs={12}>
              <TextField
                label="API URL"
                value={importConfig.other_config.base_api}
                onChange={handleChangeOtherConfig("base_api")}
                helperText={
                  importConfig.platform === 'ckan' 
                    ? "e.g. https://open.canada.ca/data/api/"
                    : "e.g. https://geohub.lio.gov.on.ca"
                }
                fullWidth
              />
            </Grid>
            {importConfig.platform === 'arcgis' && languageOptions && (
              <Grid xs={12} md={6}>
                <FormControl fullWidth variant="outlined">
                  <InputLabel id="import-language-label" shrink>
                    Language
                  </InputLabel>
                  <Select
                    labelId="import-language-label"
                    value={importConfig.other_config.language || ""}
                    label="Language"
                    onChange={handleChangeOtherConfig("language")}
                    disabled={languageLoading}
                  >
                    <MenuItem value="">
                      <em>Auto (portal culture)</em>
                    </MenuItem>
                    {languageOptions.languages.map((code) => (
                      <MenuItem key={code} value={code}>
                        {languageOptions.labels?.[code] || code.toUpperCase()}
                      </MenuItem>
                    ))}
                  </Select>
                  <FormHelperText>Choose one of the supported languages.</FormHelperText>
                </FormControl>
              </Grid>
            )}

            {importConfig.platform === 'arcgis' && (
              <Grid xs={12} md={6}>
                <CronScheduleEditor
                  idPrefix="refresh"
                  label="Update Check Schedule"
                  presetValue={refreshCronPreset}
                  presets={refreshCronPresets}
                  onPresetChange={handleChangeRefreshCronPreset}
                  customCron={refreshCustomCron}
                  onCustomCronChange={handleChangeRefreshCustomCron}
                  selectHelperText={props.globalArcgisRefreshCron
                    ? `This per-config schedule overrides the global update-check schedule: ${props.globalArcgisRefreshCron}. Each scheduled run checks upstream source_last_updated and only updates datasets that changed.`
                    : "Set when this ArcGIS auto import should check upstream source_last_updated. Each scheduled run only updates datasets that changed; unchanged datasets are skipped."}
                  previewLabel="Update Check Schedule Preview"
                  previewValue={
                    refreshCronPreset === 'custom'
                      ? buildCron(refreshCustomCron)
                      : (refreshCronPresets.find((preset) => preset.id === refreshCronPreset)?.cron || props.globalArcgisRefreshCron || '')
                  }
                  summaryText={getRefreshCronSummary(
                    importConfig.other_config.source_last_updated_cron_schedule || '',
                    refreshCustomCron,
                    props.globalArcgisRefreshCron
                  )}
                  customGridColumns="repeat(3, minmax(0, 1fr))"
                  dayOfWeekFullWidth={false}
                />
              </Grid>
            )}

            <Grid xs={12} sx={{ mt: 2 }}>
              <FormControl fullWidth variant="standard">
                <InputLabel shrink sx={{ fontSize: "22px", fontWeight: 600, mb: 10 }}>
                  Delete previously imported packages and Run full import <Box component="span" sx={{ fontWeight: 700 }}>next time</Box>
                </InputLabel>
                <Box sx={{ pt: 3 }}>
                  <Switch color="primary" checked={importConfig.other_config.delete_previously_imported} onChange={handleSwitchChangeDelete} />
                </Box>
              </FormControl>

            </Grid>

            {importConfig.platform === 'ckan' && (
              <>
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

            {importConfig.platform === 'arcgis' && (
              <Grid xs={12}>
                <Autocomplete
                  options={props.organizations}
                  getOptionLabel={(option) => option.display_name}
                  value={props.organizations.find(org => org.id === importConfig.owner_org) || null}
                  onChange={handleChangeOrganization}
                  renderInput={(params) => <TextField {...params} label="Organization" helperText="All imported datasets will be added to this organization" />}
                />
              </Grid>
            )}
          </>
        )}

        {importConfig.platform !== 'arcgis' && (
          <Grid xs={12}>
            <CronScheduleEditor
              idPrefix="cron"
              label="Cron Schedule"
              presetValue={cronPreset}
              presets={cronPresets}
              onPresetChange={handleChangeCronPreset}
              customCron={customCron}
              onCustomCronChange={handleChangeCustomCron}
              selectHelperText="Choose a preset or customize with dropdowns."
              previewLabel="Cron Preview"
              previewValue={cronPreset === "custom"
                ? buildCron(customCron)
                : (cronPresets.find((preset) => preset.id === cronPreset)?.cron || "")}
              summaryText={getCronSummary(importConfig.cron_schedule, customCron)}
              customGridColumns="repeat(5, minmax(160px, 1fr))"
              dayOfWeekFullWidth={false}
            />
          </Grid>
        )}

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
                  placeholder={getCodePlaceholder()}
                  minHeight="400px"
                  maxHeight='800px'
                  onChange={handleChangeCode}
                  extensions={[python()]}
                />
              </Box>
            </FormControl>
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
