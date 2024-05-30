import React, { useState, useEffect, useRef } from 'react';
import { Box, Typography, Button, Container, CircularProgress, Alert } from '@mui/material';
import { useCodeMirror } from '@uiw/react-codemirror';
import { json } from '@codemirror/lang-json';
import { getConfig, updateConfig } from '../api';
import { validateConfig } from './utils';
import { qaPageConfig } from './maturityLevels';

const ConfigManagementPage: React.FC = () => {
  const [config, setConfigState] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
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
        const configData = await getConfig('ckanext.udc_react.qa_maturity_levels');
        JSON.parse(configData); // Ensure the fetched data is valid JSON
        setConfigState(configData);
      } catch (error) {
        console.error('Failed to fetch config, using fallback config', error);
        setConfigState(JSON.stringify(qaPageConfig, null, 2));
        setError('Failed to load configuration from server, using fallback configuration.');
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
      const validation = validateConfig(config);
      if (!validation.valid) {
        throw new Error(validation.message);
      }
      await updateConfig('ckanext.udc_react.qa_maturity_levels', config); // Save the JSON string directly
      setSuccess('Configuration saved successfully!');
    } catch (error) {
      console.error('Failed to save config', error);
      setError(`Failed to save configuration: ${error.message}`);
    }
    setLoading(false);
  };

  return (
    <Container>
      <Typography variant="h4" gutterBottom>
        Manage Configuration
      </Typography>
      {loading && <CircularProgress />}
      {error && <Alert severity="error">{error}</Alert>}
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

export default ConfigManagementPage;
