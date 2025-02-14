import React, { useState, useEffect } from 'react';
import { Box, Typography, Button, Container, CircularProgress, Alert, TextField, FormControlLabel, Checkbox, FormHelperText } from '@mui/material';
import { useApi } from '../api/useApi';

interface IChatGPTConfig {
  openai_key: string;
  openai_model: string;
  max_tokens: number;
  temperature: number;
  use_markdown: boolean;
  use_custom_prompt: boolean;
  custom_prompt: string;
}

const ChatGPTSummarySettings: React.FC = () => {
  const { api, executeApiCall } = useApi();

  const [config, setConfigState] = useState<IChatGPTConfig>({
    openai_key: '',
    openai_model: '',
    max_tokens: 0,
    temperature: 0,
    use_markdown: false,
    use_custom_prompt: false,
    custom_prompt: '',
  });
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [defaultConfig, setDefaultConfig] = useState<IChatGPTConfig>();

  useEffect(() => {
    const fetchConfig = async () => {
      setLoading(true);
      const defaultConfig_ = await api.getDefaultAISummaryConfig();
      setDefaultConfig(defaultConfig_);

      try {
        const configData = await executeApiCall(() => api.getConfig('ckanext.udc.desc.config'));
        const config = JSON.parse(configData);
        if (config.custom_prompt === '' || config.custom_prompt == null) {
          config.custom_prompt = defaultConfig_.custom_prompt;
        }
        console.log('Config:', config);
        setConfigState(config);

      } catch (error) {
        console.error('Failed to fetch config, using fallback config', error);
        setError('Failed to load configuration from server. using default configuration.');
        setConfigState(defaultConfig_);
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
        <Box sx={{ mb: 2 }}>
          <FormControlLabel
            control={
              <Checkbox
                checked={config.use_markdown && !config.use_custom_prompt}
                onChange={(e) => setConfigState(prev => ({ ...prev, use_markdown: e.target.checked }))}
                name="use_markdown"
                disabled={config.use_custom_prompt}
              />
            }
            label="Use and Prefer Markdown"
          />
        </Box>
        <Box sx={{ mb: 2 }}>
          <FormControlLabel
            control={
              <Checkbox
                checked={config.use_custom_prompt}
                onChange={(e) => setConfigState(prev => ({ ...prev, use_custom_prompt: e.target.checked }))}
                name="use_custom_prompt"
              />
            }
            label="Use Custom Prompt"
          />
          <FormHelperText sx={{ mb: 2 }}>
            If enabled, the custom prompt will be used instead of the default prompt.
          </FormHelperText>
        </Box>
        {config.use_custom_prompt && 
          <Box>
            <TextField
              fullWidth
              label="Custom Prompt"
              name="custom_prompt"
              value={config.custom_prompt}
              onChange={handleChange}
              sx={{ mb: 2 }}
              multiline
            />
            <Button
              variant="text"
              color="secondary"
              onClick={() => setConfigState(prev => ({ ...prev, custom_prompt: defaultConfig?.custom_prompt || '' }))}
              sx={{ mb: 2 }}
            >
              Reset to Default Prompt
            </Button>
          </Box>
        }
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
