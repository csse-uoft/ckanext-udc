import React, { useState, useEffect, useRef } from 'react';
import { Box, Typography, Button, Container, CircularProgress, Alert, Paper, Switch, FormControlLabel, Stack } from '@mui/material';
import { useCodeMirror } from '@uiw/react-codemirror';
import { json } from '@codemirror/lang-json';
import { useApi } from '../api/useApi';

/**
 * Render an error message.
 * Example error:
{
  "help": "http://.../api/3/action/help_show?name=config_option_update",
  "error": {
      "ckanext.udc.config": [
          "UDC Config: Malformed JSON Format."
      ],
      "__type": "Validation Error"
  },
  "success": false
}
 */
function renderError(error: any) {
  if (error.error && error.error.__type === 'Validation Error') {
    // loop each key in error.error and render the error message
    const alerts = [];
    for (const key in error.error) {
      if (key !== '__type') {
        alerts.push(<Alert sx={{whiteSpace: 'pre'}} severity="error">{error.error.__type + ':\n'}{error.error[key].join('\n')}</Alert>);
      }
    }

    return alerts;
  }

}

function parseBooleanConfig(value: any) {
  if (typeof value === 'boolean') {
    return value;
  }

  if (value == null) {
    return false;
  }

  return ['1', 'true', 'yes', 'on'].includes(String(value).trim().toLowerCase());
}

const UDRCConfigPage: React.FC = () => {
  const { api, executeApiCall } = useApi();

  const [config, setConfigState] = useState<string>('');
  const [maintenanceMode, setMaintenanceMode] = useState<boolean>(false);
  const [appliedMaintenanceMode, setAppliedMaintenanceMode] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<any>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [maintenanceError, setMaintenanceError] = useState<any>(null);
  const [maintenanceSuccess, setMaintenanceSuccess] = useState<string | null>(null);
  const editorRef = useRef<HTMLDivElement>(null);

  const { setContainer } = useCodeMirror({
    container: editorRef.current,
    extensions: [json()],
    value: config,
    height: "600px",
    basicSetup: {
      lineNumbers: true,
    },
    onChange: (value) => setConfigState(value),
  });

  useEffect(() => {
    if (editorRef.current) {
      setContainer(editorRef.current);
    }
  }, [editorRef.current, setContainer]);

  useEffect(() => {
    const fetchConfig = async () => {
      setLoading(true);
      try {
        const [configData, maintenanceModeValue] = await Promise.all([
          executeApiCall(() => api.getConfig('ckanext.udc.config')),
          executeApiCall(() => api.getConfig('ckanext.udc.maintenance_mode')),
        ]);
        JSON.parse(configData); // Ensure the fetched data is valid JSON
        setConfigState(configData);
        const parsedMaintenanceMode = parseBooleanConfig(maintenanceModeValue);
        setMaintenanceMode(parsedMaintenanceMode);
        setAppliedMaintenanceMode(parsedMaintenanceMode);
      } catch (error) {
        console.error('Failed to fetch config', error);
        setError('Failed to load configuration.');
      }
      setLoading(false);
    };

    fetchConfig();
  }, []);

  const handleSave = async () => {
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      await executeApiCall(() => api.updateConfig('ckanext.udc.config', config)); // Save the JSON string directly
      setSuccess('Configuration saved successfully!');
    } catch (error: any) {
      console.error('Failed to save config', error);
      setError(error);
    }
    setLoading(false);
  };

  const handleSaveMaintenanceMode = async () => {
    setLoading(true);
    setMaintenanceError(null);
    setMaintenanceSuccess(null);

    try {
      await executeApiCall(() => api.updateConfig('ckanext.udc.maintenance_mode', maintenanceMode ? 'true' : 'false'));
      setAppliedMaintenanceMode(maintenanceMode);
      setMaintenanceSuccess('Maintenance mode updated successfully!');
    } catch (error: any) {
      console.error('Failed to save maintenance mode', error);
      setMaintenanceError(error);
    }

    setLoading(false);
  };

  return (
    <Container>
      <Paper sx={{ p: 3, mb: 3, borderRadius: 3, border: '1px solid', borderColor: appliedMaintenanceMode ? 'warning.light' : 'divider', backgroundColor: appliedMaintenanceMode ? 'warning.50' : 'background.paper' }}>
        <Stack spacing={2}>
          <Box>
            <Typography variant="h5" gutterBottom>
              Site Maintenance Mode
            </Typography>
            <Typography variant="body2" color="text.secondary">
              When enabled, public HTML pages outside the UDRC dashboard are replaced with the maintenance page. The dashboard, login, APIs, and static assets remain available.
            </Typography>
          </Box>
          {maintenanceError && renderError(maintenanceError)}
          {maintenanceSuccess && <Alert severity="success">{maintenanceSuccess}</Alert>}
          {appliedMaintenanceMode && (
            <Alert severity="warning">
              Maintenance mode is currently enabled. Public pages are returning the maintenance page.
            </Alert>
          )}
          {maintenanceMode !== appliedMaintenanceMode && (
            <Alert severity="info">
              You have unsaved maintenance mode changes. Save to apply the current toggle state.
            </Alert>
          )}
          <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 2 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={maintenanceMode}
                  onChange={(event) => setMaintenanceMode(event.target.checked)}
                  color="warning"
                />
              }
              label={maintenanceMode ? 'Enabled' : 'Disabled'}
            />
            <Button
              variant="contained"
              color={maintenanceMode ? 'warning' : 'primary'}
              onClick={handleSaveMaintenanceMode}
              disabled={loading}
            >
              Save Maintenance Mode
            </Button>
          </Box>
        </Stack>
      </Paper>
      <Typography variant="h5" gutterBottom>
        Maturity Model & Mapping JSON (UDC Config)
      </Typography>
      {loading && <CircularProgress />}
      {error && renderError(error)}
      {success && <Alert severity="success">{success}</Alert>}
      <Box sx={{ marginTop: 2 }}>
        <div ref={editorRef} style={{ height: '600px', overflowX: 'auto' }} />
      </Box>
      <Button
        variant="contained"
        color="primary"
        sx={{ marginTop: 2 }}
        onClick={handleSave}
        disabled={loading}
      >
        Save Configuration
      </Button>
    </Container>
  );
};

export default UDRCConfigPage;
