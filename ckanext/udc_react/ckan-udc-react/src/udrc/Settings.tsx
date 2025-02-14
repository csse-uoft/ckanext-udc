import React, { useState, useEffect, useRef } from 'react';
import { Box, Typography, Button, Container, CircularProgress, Alert } from '@mui/material';
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

const UDRCConfigPage: React.FC = () => {
  const { api, executeApiCall } = useApi();

  const [config, setConfigState] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<any>(null);
  const [success, setSuccess] = useState<string | null>(null);
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
        const configData = await executeApiCall(() => api.getConfig('ckanext.udc.config'));
        JSON.parse(configData); // Ensure the fetched data is valid JSON
        setConfigState(configData);
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

  return (
    <Container>
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
