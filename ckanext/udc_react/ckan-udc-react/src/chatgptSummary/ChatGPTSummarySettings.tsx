import React, { useState, useEffect } from 'react';
import { Box, Typography, Button, Container, CircularProgress, Alert, TextField } from '@mui/material';
import { useApi } from '../api/useApi';

interface IChatGPTConfig {
  openai_key: string;
  openai_model: string;
  max_tokens: number;
  temperature: number;
}

const ChatGPTSummarySettings: React.FC = () => {
  const { api, executeApiCall } = useApi();

  const [config, setConfigState] = useState<IChatGPTConfig>({
    openai_key: '',
    openai_model: '',
    max_tokens: 0,
    temperature: 0,
  });
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    const fetchConfig = async () => {
      setLoading(true);
      try {
        const configData = await executeApiCall(() => api.getConfig('ckanext.udc.desc.config'));
        setConfigState(JSON.parse(configData));
      } catch (error) {
        console.error('Failed to fetch config, using fallback config', error);
        setError('Failed to load configuration from server.');
      }
      setLoading(false);
    };

    fetchConfig();
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setConfigState(prevState => ({
      ...prevState,
      [name]: value,
    }));
  };

  const handleChangeNumber = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setConfigState(prevState => ({
      ...prevState,
      [name]: Number(value),
    }));
  };


  const handleSave = async () => {
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      await executeApiCall(() => api.updateConfig('ckanext.udc.desc.config', JSON.stringify(config))); // Save the JSON string directly
      setSuccess('Configuration saved successfully!');
    } catch (error: any) {
      console.error('Failed to save config', error);
      setError(`Failed to save configuration: ${error.message}`);
    }
    setLoading(false);
  };

  return (
    <Container>
      <Typography variant="h4" gutterBottom>
        ChatGPT Summary Configuration
      </Typography>
      {loading && <CircularProgress />}
      {error && <Alert severity="error">{error}</Alert>}
      {success && <Alert severity="success">{success}</Alert>}

      <Box sx={{ mt: 2 }}>
        <TextField
          fullWidth
          label="OpenAI Key"
          name="openai_key"
          value={config.openai_key}
          onChange={handleChange}
          sx={{ mb: 2 }}
        />
        <TextField
          fullWidth
          label="OpenAI Model"
          name="openai_model"
          value={config.openai_model}
          onChange={handleChange}
          sx={{ mb: 2 }}
        />
        <TextField
          fullWidth
          label="Max Tokens"
          name="max_tokens"
          type="number"
          value={config.max_tokens}
          onChange={() => handleChangeNumber}
          sx={{ mb: 2 }}
        />
        <TextField
          fullWidth
          label="Temperature"
          name="temperature"
          type="number"
          value={config.temperature}
          onChange={handleChangeNumber}
          sx={{ mb: 2 }}
        />
        <Button
          variant="contained"
          color="primary"
          sx={{ marginTop: 2 }}
          onClick={handleSave}
          disabled={loading}
        >
          Save Configuration
        </Button>
      </Box>
    </Container>
  );
};

export default ChatGPTSummarySettings;
