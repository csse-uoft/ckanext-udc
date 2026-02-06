import { Paper, Box, InputLabel, FormControl, Button, Divider, Switch, TextField, Autocomplete, FormControlLabel, RadioGroup, Radio, CircularProgress, Select, MenuItem, FormHelperText } from '@mui/material';
import Grid from '@mui/material/Unstable_Grid2'; // Grid version 2
import CodeMirror from "@uiw/react-codemirror";
import { python } from '@codemirror/lang-python';
import { useEffect, useMemo, useState } from 'react';
import { SaveOutlined, PlayArrowOutlined, DeleteForeverOutlined } from '@mui/icons-material';
import { useApi } from '../api/useApi';
import { CKANOrganization, ImportLanguageOptions } from '../api/api';
import OrganizationMapper from './mapper/OrganizationMapper';
import { REACT_PATH } from '../constants';

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
    };
    cron_schedule?: string;
    platform?: string;
    created_at?: string | null;
    updated_at?: string | null;
  };
  onUpdate: (option?: string) => void;
  organizations: CKANOrganization[];
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

const defaultCustomCron = {
  minute: ["*"],
  hour: ["*"],
  dayOfMonth: ["*"],
  month: ["*"],
  dayOfWeek: ["*"],
};

const range = (start: number, end: number) =>
  Array.from({ length: end - start + 1 }, (_, index) => String(start + index));

const dayOfWeekLabels: Record<string, string> = {
  "0": "Sun",
  "1": "Mon",
  "2": "Tue",
  "3": "Wed",
  "4": "Thu",
  "5": "Fri",
  "6": "Sat",
};

const monthLabels: Record<string, string> = {
  "1": "Jan",
  "2": "Feb",
  "3": "Mar",
  "4": "Apr",
  "5": "May",
  "6": "Jun",
  "7": "Jul",
  "8": "Aug",
  "9": "Sep",
  "10": "Oct",
  "11": "Nov",
  "12": "Dec",
};

const customCronOptions = {
  minute: ["*", ...range(0, 59)],
  hour: ["*", ...range(0, 23)],
  dayOfMonth: ["*", ...range(1, 31)],
  month: ["*", ...range(1, 12)],
  dayOfWeek: ["*", ...range(0, 6)],
};

const compactSelection = (values: string[]) => {
  if (!values.length) {
    return "*";
  }
  if (values.includes("*")) {
    return "*";
  }
  return values.join(",");
};

const formatSelection = (values: string[], labelMap?: Record<string, string>) => {
  if (!values.length || values.includes("*")) {
    return "any";
  }
  const labels = labelMap
    ? values.map((value) => labelMap[value] || value)
    : values;
  return labels.join(", ");
};

const formatTime = (hour: string, minute: string) => {
  const hourNum = Number(hour);
  const minuteNum = Number(minute);
  if (Number.isNaN(hourNum) || Number.isNaN(minuteNum)) {
    return `${hour}:${minute}`;
  }
  const suffix = hourNum >= 12 ? "PM" : "AM";
  const hour12 = hourNum % 12 === 0 ? 12 : hourNum % 12;
  return `${hour12}:${String(minuteNum).padStart(2, "0")} ${suffix}`;
};

const getCronSummary = (cron: string, customCron: typeof defaultCustomCron) => {
  if (!cron) {
    return "No schedule selected yet.";
  }

  const minute = compactSelection(customCron.minute);
  const hour = compactSelection(customCron.hour);
  const dayOfMonth = compactSelection(customCron.dayOfMonth);
  const month = compactSelection(customCron.month);
  const dayOfWeek = compactSelection(customCron.dayOfWeek);

  const isSingleMinute = !minute.includes(",") && minute !== "*";
  const isSingleHour = !hour.includes(",") && hour !== "*";
  const isSingleDayOfMonth = !dayOfMonth.includes(",") && dayOfMonth !== "*";
  const isSingleMonth = !month.includes(",") && month !== "*";
  const isWeekday = dayOfWeek === "1,2,3,4,5";
  const isEveryDay = dayOfWeek === "*" && dayOfMonth === "*" && month === "*";

  if (isSingleMinute && isSingleHour && isWeekday && dayOfMonth === "*" && month === "*") {
    return `Every weekday at ${formatTime(hour, minute)}.`;
  }
  if (isSingleMinute && isSingleHour && isEveryDay) {
    return `Every day at ${formatTime(hour, minute)}.`;
  }
  if (isSingleMinute && isSingleHour && isSingleDayOfMonth && month === "*" && dayOfWeek === "*") {
    return `Every month on day ${dayOfMonth} at ${formatTime(hour, minute)}.`;
  }
  if (isSingleMinute && isSingleHour && isSingleDayOfMonth && isSingleMonth && dayOfWeek === "*") {
    const monthLabel = monthLabels[month] || month;
    return `Every year on ${monthLabel} ${dayOfMonth} at ${formatTime(hour, minute)}.`;
  }

  return `Runs at minute ${formatSelection(customCron.minute)}, hour ${formatSelection(customCron.hour)}, day of month ${formatSelection(customCron.dayOfMonth)}, month ${formatSelection(customCron.month, monthLabels)}, day of week ${formatSelection(customCron.dayOfWeek, dayOfWeekLabels)}.`;
};

const buildCron = (customCron: typeof defaultCustomCron) =>
  `${compactSelection(customCron.minute)} ${compactSelection(customCron.hour)} ${compactSelection(customCron.dayOfMonth)} ${compactSelection(customCron.month)} ${compactSelection(customCron.dayOfWeek)}`.trim();

const parseCron = (cron: string) => {
  if (!cron) {
    return { ...defaultCustomCron };
  }
  const parts = cron.trim().split(/\s+/);
  if (parts.length < 5) {
    return { ...defaultCustomCron };
  }
  return {
    minute: (parts[0] || "*").split(","),
    hour: (parts[1] || "*").split(","),
    dayOfMonth: (parts[2] || "*").split(","),
    month: (parts[3] || "*").split(","),
    dayOfWeek: (parts[4] || "*").split(","),
  };
};

const resolveCronPreset = (cron: string) => {
  const preset = cronPresets.find((item) => item.cron === cron);
  return preset ? preset.id : "custom";
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
  const [cronPreset, setCronPreset] = useState(() => resolveCronPreset(importConfig.cron_schedule));
  const [customCron, setCustomCron] = useState(() => parseCron(importConfig.cron_schedule));
  const [languageLoading, setLanguageLoading] = useState(false);

  useEffect(() => {
    setImportConfig(buildImportConfig(props.defaultConfig));
  }, [props.defaultConfig?.uuid]);

  useEffect(() => {
    const preset = resolveCronPreset(importConfig.cron_schedule);
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

  const handleChangeCronPreset = (e: any) => {
    const value = e.target.value as string;
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

  const handleChangeCustomCron = (field: keyof typeof defaultCustomCron) => (e: any) => {
    const value = (e.target.value as string[]) || [];
    const cleaned = value.includes("*") && value.length > 1
      ? value.filter((item) => item !== "*")
      : value;
    const normalized = cleaned.length ? cleaned : ["*"];
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

        <Grid xs={12}>
          <FormControl fullWidth sx={{ mt: 1 }} variant="outlined">
            <InputLabel id="cron-preset-label" shrink>
              Cron Schedule
            </InputLabel>
            <Select
              labelId="cron-preset-label"
              value={cronPreset}
              label="Cron Schedule"
              onChange={handleChangeCronPreset}
            >
              {cronPresets.map((preset) => (
                <MenuItem key={preset.id} value={preset.id}>
                  {preset.label}
                </MenuItem>
              ))}
            </Select>
            <FormHelperText>
              Choose a preset or customize with dropdowns.
            </FormHelperText>
          </FormControl>

          {cronPreset === "custom" && (
            <Grid container spacing={2} sx={{ mt: 1 }}>
              <Grid xs={12} sm={6} md="auto">
                <FormControl fullWidth variant="outlined" sx={{ minWidth: 160 }}>
                  <InputLabel id="cron-minute-label" shrink>
                    Minute
                  </InputLabel>
                  <Select
                    labelId="cron-minute-label"
                    value={customCron.minute}
                    label="Minute"
                    onChange={handleChangeCustomCron("minute")}
                    multiple
                  >
                    {customCronOptions.minute.map((value) => (
                      <MenuItem key={value} value={value}>
                        {value}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid xs={12} sm={6} md="auto">
                <FormControl fullWidth variant="outlined" sx={{ minWidth: 160 }}>
                  <InputLabel id="cron-hour-label" shrink>
                    Hour
                  </InputLabel>
                  <Select
                    labelId="cron-hour-label"
                    value={customCron.hour}
                    label="Hour"
                    onChange={handleChangeCustomCron("hour")}
                    multiple
                  >
                    {customCronOptions.hour.map((value) => (
                      <MenuItem key={value} value={value}>
                        {value}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid xs={12} sm={6} md="auto">
                <FormControl fullWidth variant="outlined" sx={{ minWidth: 160 }}>
                  <InputLabel id="cron-day-month-label" shrink>
                    Day of Month
                  </InputLabel>
                  <Select
                    labelId="cron-day-month-label"
                    value={customCron.dayOfMonth}
                    label="Day of Month"
                    onChange={handleChangeCustomCron("dayOfMonth")}
                    multiple
                  >
                    {customCronOptions.dayOfMonth.map((value) => (
                      <MenuItem key={value} value={value}>
                        {value}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid xs={12} sm={6} md="auto">
                <FormControl fullWidth variant="outlined" sx={{ minWidth: 160 }}>
                  <InputLabel id="cron-month-label" shrink>
                    Month
                  </InputLabel>
                  <Select
                    labelId="cron-month-label"
                    value={customCron.month}
                    label="Month"
                    onChange={handleChangeCustomCron("month")}
                    multiple
                  >
                    {customCronOptions.month.map((value) => (
                      <MenuItem key={value} value={value}>
                        {monthLabels[value] || value}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid xs={12} sm={6} md="auto">
                <FormControl fullWidth variant="outlined" sx={{ minWidth: 160 }}>
                  <InputLabel id="cron-day-week-label" shrink>
                    Day of Week
                  </InputLabel>
                  <Select
                    labelId="cron-day-week-label"
                    value={customCron.dayOfWeek}
                    label="Day of Week"
                    onChange={handleChangeCustomCron("dayOfWeek")}
                    multiple
                  >
                    {customCronOptions.dayOfWeek.map((value) => (
                      <MenuItem key={value} value={value}>
                        {dayOfWeekLabels[value] || value}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid xs={12} md={6}>
                <TextField
                  label="Cron Preview"
                  value={buildCron(customCron)}
                  fullWidth
                  InputProps={{ readOnly: true }}
                />
                <FormHelperText sx={{ mt: 1 }}>
                  {getCronSummary(importConfig.cron_schedule, customCron)}
                </FormHelperText>
              </Grid>
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
