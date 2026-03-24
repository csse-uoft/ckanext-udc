import { Box, FormControl, FormHelperText, InputLabel, MenuItem, Select, TextField } from "@mui/material";

import {
  CronPreset,
  CustomCronField,
  CustomCronState,
  customCronOptions,
  dayOfWeekLabels,
  monthLabels,
} from "../utils/cron";

interface CronScheduleEditorProps {
  idPrefix: string;
  label: string;
  presetValue: string;
  presets: CronPreset[];
  onPresetChange: (value: string) => void;
  customCron: CustomCronState;
  onCustomCronChange: (field: CustomCronField, value: string[]) => void;
  selectHelperText?: string;
  previewLabel?: string;
  previewValue: string;
  summaryText?: string;
  customGridColumns?: string;
  dayOfWeekFullWidth?: boolean;
}

const fieldLabel: Record<CustomCronField, string> = {
  minute: "Minute",
  hour: "Hour",
  dayOfMonth: "Day of Month",
  month: "Month",
  dayOfWeek: "Day of Week",
};

const fieldOrder: CustomCronField[] = ["minute", "hour", "dayOfMonth", "month", "dayOfWeek"];

export default function CronScheduleEditor(props: CronScheduleEditorProps) {
  const {
    idPrefix,
    label,
    presetValue,
    presets,
    onPresetChange,
    customCron,
    onCustomCronChange,
    selectHelperText,
    previewLabel = "Cron Preview",
    previewValue,
    summaryText,
    customGridColumns = "repeat(2, minmax(0, 1fr))",
    dayOfWeekFullWidth = true,
  } = props;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <FormControl fullWidth variant="outlined">
        <InputLabel id={`${idPrefix}-preset-label`} shrink>
          {label}
        </InputLabel>
        <Select
          labelId={`${idPrefix}-preset-label`}
          value={presetValue}
          label={label}
          onChange={(event) => onPresetChange(event.target.value as string)}
        >
          {presets.map((preset) => (
            <MenuItem key={preset.id} value={preset.id}>
              {preset.label}
            </MenuItem>
          ))}
        </Select>
        {selectHelperText ? <FormHelperText>{selectHelperText}</FormHelperText> : null}
      </FormControl>

      {presetValue === "custom" ? (
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: customGridColumns }, gap: 2 }}>
          {fieldOrder.map((field) => {
            const labelText = fieldLabel[field];
            const options = customCronOptions[field];
            const optionLabels = field === "month" ? monthLabels : field === "dayOfWeek" ? dayOfWeekLabels : undefined;
            const sx = field === "dayOfWeek" && dayOfWeekFullWidth ? { gridColumn: { md: "1 / span 2" } } : undefined;

            return (
              <FormControl key={field} fullWidth variant="outlined" sx={sx}>
                <InputLabel id={`${idPrefix}-${field}-label`} shrink>
                  {labelText}
                </InputLabel>
                <Select
                  labelId={`${idPrefix}-${field}-label`}
                  value={customCron[field]}
                  label={labelText}
                  onChange={(event) => onCustomCronChange(field, (event.target.value as string[]) || [])}
                  multiple
                >
                  {options.map((value) => (
                    <MenuItem key={value} value={value}>
                      {optionLabels?.[value] || value}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            );
          })}
        </Box>
      ) : null}

      <TextField label={previewLabel} value={previewValue} fullWidth InputProps={{ readOnly: true }} />
      {summaryText ? <FormHelperText sx={{ mt: -1 }}>{summaryText}</FormHelperText> : null}
    </Box>
  );
}