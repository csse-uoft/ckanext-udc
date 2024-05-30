const baseURL = window.location.origin;

export async function fetchWithErrorHandling(url: string, options?: RequestInit) {
  const response = await fetch(url, options);
  const data = await response.json();

  if (!response.ok) {
    throw data;
  }

  return data;
}

export async function getImportConfigs() {
  const importConfig = await fetchWithErrorHandling(baseURL + "/api/3/action/cudc_import_configs_get");
  return importConfig.result;
}

export async function updateImportConfig(importConfig: { uuid?: string, name: string, code: string }) {
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/cudc_import_config_update", {
    method: "POST",
    body: JSON.stringify({ import_config: importConfig }),
    headers: {
      "Content-Type": "application/json",
    }
  });
  return result;
}

export async function deleteImportConfig(importConfigUUID: string) {
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/cudc_import_config_delete", {
    method: "POST",
    body: JSON.stringify({ uuid: importConfigUUID }),
    headers: {
      "Content-Type": "application/json",
    }
  });

  return result.result;
}

export async function runImport(importUUID: string) {
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/cudc_import_run", {
    method: "POST",
    body: JSON.stringify({ uuid: importUUID }),
    headers: {
      "Content-Type": "application/json",
    }
  });

  return result.result;
}

export async function getImportStatus() {
  const importConfig = await fetchWithErrorHandling(baseURL + "/api/3/action/cudc_import_status_get");
  return importConfig.result;
}

export async function getImportLogsByConfigId(configId: string) {
  const importConfig = await fetchWithErrorHandling(baseURL + "/api/3/action/cudc_import_logs_get?config_id=" + configId);
  return importConfig.result;
}

export async function deleteImportLog(logId: string) {
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/cudc_import_log_delete", {
    method: "POST",
    body: JSON.stringify({ id: logId }),
    headers: {
      "Content-Type": "application/json",
    }
  });

  return result.result;
}

export async function getConfig(configKey: string) {
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/config_option_show?key=" + configKey);
  return result.result;
}

// Pulic API
export async function getMaturityLevels() {
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/get_maturity_levels");
  return result.result;
}

export async function updateConfig(configKey: string, value: string) {
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/config_option_update", {
    method: "POST",
    body: JSON.stringify({ [configKey]: value }),
    headers: {
      "Content-Type": "application/json",
    }
  });

  if (!result.success) {
    throw result.error;
  }
}
