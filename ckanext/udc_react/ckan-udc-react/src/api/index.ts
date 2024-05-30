const baseURL = window.location.origin;

export async function getImportConfigs() {
  const result = await fetch(baseURL + "/api/3/action/cudc_import_configs_get");
  const importConfig = await result.json();
  return importConfig.result;
}

export async function updateImportConfig(importConfig: { uuid?: string, name: string, code: string }) {
  const result = await fetch(baseURL + "/api/3/action/cudc_import_config_update", {
    method: "POST",
    body: JSON.stringify({ import_config: importConfig }),
    headers: {
      "Content-Type": "application/json",
    }
  });
  return await result.json();
}

export async function deleteImportConfig(importConfigUUID: string) {
  const result = await fetch(baseURL + "/api/3/action/cudc_import_config_delete", {
    method: "POST",
    body: JSON.stringify({ uuid: importConfigUUID }),
    headers: {
      "Content-Type": "application/json",
    }
  });

  const importConfig = await result.json();
  return importConfig.result;
}


export async function runImport(importUUID: string) {
  const result = await fetch(baseURL + "/api/3/action/cudc_import_run", {
    method: "POST",
    body: JSON.stringify({ uuid: importUUID }),
    headers: {
      "Content-Type": "application/json",
    }
  });

  const importConfig = await result.json();
  return importConfig.result;
}

export async function getImportStatus() {
  const result = await fetch(baseURL + "/api/3/action/cudc_import_status_get");
  const importConfig = await result.json();
  return importConfig.result;
}

export async function getImportLogsByConfigId(configId: string) {
  const result = await fetch(baseURL + "/api/3/action/cudc_import_logs_get?config_id=" + configId);
  const importConfig = await result.json();
  return importConfig.result;
}

export async function deleteImportLog(logId: string) {
  const result = await fetch(baseURL + "/api/3/action/cudc_import_log_delete", {
    method: "POST",
    body: JSON.stringify({ id: logId }),
    headers: {
      "Content-Type": "application/json",
    }
  });

  const importConfig = await result.json();
  return importConfig.result;
}

export async function getConfig(configKey: string) {
  const result = await fetch(baseURL + "/api/3/action/config_option_show?key=" + configKey);
  return (await result.json()).result;
}

// Pulic API
export async function getMaturityLevels() {
  const result = await fetch(baseURL + "/api/3/action/get_maturity_levels");
  return (await result.json()).result;
}


export async function updateConfig(configKey: string, value: string) {
  const result = await fetch(baseURL + "/api/3/action/config_option_update", {
    method: "POST",
    body: JSON.stringify({ [configKey]: value }),
    headers: {
      "Content-Type": "application/json",
    }
  });
  const response = (await result.json());
  if (!response.success) {
    return response.error;
  } 
}