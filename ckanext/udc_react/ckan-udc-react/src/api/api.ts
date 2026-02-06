const baseURL = window.location.origin;

export async function fetchWithErrorHandling(url: string, options?: RequestInit) {
  try {
    const response = await fetch(url, options);
    const data = await response.json();

    if (response.status === 403) {
      throw data;
    }

    if (!response.ok) {
      if (data?.error?.message) {
        throw data.error.message;
      } else {
        throw data;
      }
    }

    return data;
  } catch (error: any) {
    if (error?.response) {
      const jsonError = await error.response.json(); // must await for response
      if (jsonError?.error?.message) {
        throw jsonError.error.message;
      } else {
        throw jsonError;
      }
    } else {
      throw error
    }

  }

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

export async function getDefaultAISummaryConfig() {
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/default_ai_summary_config");
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

export interface CKANOrganization {
  approval_status: string;
  created: string;
  description: string;
  display_name: string;
  id: string;
  image_display_url: string;
  image_url: string;
  is_organization: boolean;
  name: string;
  num_followers: number;
  package_count: number;
  state: string;
  title: string;
  type: string;
}

export interface CKANOrganizationAndAdmin {
  id: string;
  name: string;
  admins: CKANUser[];
}

export interface CKANUser {
  id: string;
  name: string;
  fullname: string;
  sysadmin?: boolean;
}

export async function getOrganizations(): Promise<CKANOrganization[]> {
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/cudc_organization_list_min");
  return result.result;
}

export async function packageShow(id: string) {
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/package_show?id=" + id);
  return result.result;
}

export async function packageSearch(q: string, rows: number, start: number, sort?: string, fq?: string) {
  const params = { q, fq, rows, start, sort, facet: 'false' };
  let paramsStr = Object.entries(params)
    .filter(([k, v]) => (k != null && v != null))
    .map(([k, v]) => {
      if (k === 'sort') {
        return `${k}=${v}`;
      } else {
        return `${k}=${encodeURIComponent(String(v))}`;
      }
    }).join('&')


  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/package_search?" + paramsStr);
  return result.result;
}

export async function generateSummary(id: string): Promise<{ prompt: string, results: string[] }> {
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/summary_generate", {
    method: "POST",
    body: JSON.stringify({ id }),
    headers: {
      "Content-Type": "application/json",
    }
  });

  if (!result.success) {
    throw result.error;
  }
  return result.result;
}

export async function update_summary(id: string, summary: string): Promise<void> {
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/update_summary", {
    method: "POST",
    body: JSON.stringify({ package_id: id, summary }),
    headers: {
      "Content-Type": "application/json",
    }
  });

  if (!result.success) {
    throw result.error;
  }
}

export async function updatePackage(id: string, data: any) {
  if (data?.related_packages) {
    delete data.related_packages;
  }
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/package_update", {
    method: "POST",
    body: JSON.stringify({ id, ...data }),
    headers: {
      "Content-Type": "application/json",
    }
  });

  if (!result.success) {
    throw result.error;
  }
}

export async function getWsToken() {
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/get_ws_token", {
    method: "GET"
  });
  if (!result.success) {
    throw result.error;
  }
  return result.result;
}

export async function getCurrentUser(): Promise<CKANUser> {
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/get_current_user");
  return result.result;
}

export async function flashMessage(messageType: string) {
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/flash_message", {
    method: "POST",
    body: JSON.stringify({ message_type: messageType }),
    headers: {
      "Content-Type": "application/json",
    },
  });
  if (!result.success) {
    throw result.error;
  }
}

export async function getOrganizationsAndAdmins(): Promise<{organizations: CKANOrganizationAndAdmin[], sysadmins: CKANUser[]}> {
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/get_organizations_and_admins", {
    method: "GET"
  });
  if (!result.success) {
    throw result.error;
  }
  return result.result;
}

export async function requestOrganizationAccess(organization: string, admins: string[], message: string) {
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/request_organization_access", {
    method: "POST",
    body: JSON.stringify({ organization_id: organization, admin_ids: admins, notes: message }),
    headers: {
      "Content-Type": "application/json",
    }
  });
  if (!result.success) {
    throw result.error;
  }
  return result.result;
}

export async function decodeOrganizationAccessToken(token: string) {
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/decode_request_organization_access_token", {
    method: "POST",
    body: JSON.stringify({ token }),
    headers: {
      "Content-Type": "application/json",
    }
  });
  if (!result.success) {
    throw result.error;
  }
  return result.result;
}

export async function approveOrDenyOrganizationAccess(token: string, approve: boolean) {
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/approve_or_deny_organization_access", {
    method: "POST",
    body: JSON.stringify({ token, approve }),
    headers: {
      "Content-Type": "application/json",
    }
  });
  if (!result.success) {
    throw result.error;
  }
  return result.result;
}

export interface License {
  id: string;
  title: string;
  url: string;
  user: {
    name: string;
    fullname?: string;
  };
}

export interface UserSummary {
  id: string;
  name: string;
  fullname?: string;
  email?: string;
  created?: string;
  state?: string;
  sysadmin?: boolean;
  about?: string;
}

export interface UserListResponse {
  results: UserSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface UserListFilters {
  q?: string;
  name?: string;
  fullname?: string;
  email?: string;
  about?: string;
  sysadmin?: boolean;
}

export interface OrganizationSummary {
  id: string;
  name: string;
  title?: string;
  description?: string;
  state?: string;
  created?: string;
}

export interface OrganizationPackageSummary {
  id: string;
  name: string;
  title?: string;
  state?: string;
  private?: boolean;
  metadata_modified?: string | null;
}

export interface OrganizationListResponse {
  results: OrganizationSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface OrganizationPackageListResponse {
  organization: OrganizationSummary;
  results: OrganizationPackageSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface OrganizationListFilters {
  q?: string;
  name?: string;
  title?: string;
  state?: string;
}

export async function listUsers(params: { page: number; page_size: number; filters?: UserListFilters }) {
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/udc_user_list", {
    method: "POST",
    body: JSON.stringify(params),
    headers: {
      "Content-Type": "application/json",
    }
  });
  if (!result.success) {
    throw result.error;
  }
  return result.result as UserListResponse;
}

export async function listOrganizations(params: {
  page: number;
  page_size: number;
  filters?: OrganizationListFilters;
}) {
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/udc_organization_list", {
    method: "POST",
    body: JSON.stringify(params),
    headers: {
      "Content-Type": "application/json",
    },
  });
  if (!result.success) {
    throw result.error;
  }
  return result.result as OrganizationListResponse;
}

export async function listOrganizationPackages(params: {
  org_id: string;
  page: number;
  page_size: number;
  filters?: OrganizationListFilters;
}) {
  const result = await fetchWithErrorHandling(
    baseURL + "/api/3/action/udc_organization_packages_list",
    {
      method: "POST",
      body: JSON.stringify(params),
      headers: {
        "Content-Type": "application/json",
      },
    }
  );
  if (!result.success) {
    throw result.error;
  }
  return result.result as OrganizationPackageListResponse;
}

export async function listOrganizationPackageIds(params: {
  org_id: string;
  filters?: OrganizationListFilters;
}) {
  const result = await fetchWithErrorHandling(
    baseURL + "/api/3/action/udc_organization_packages_ids",
    {
      method: "POST",
      body: JSON.stringify(params),
      headers: {
        "Content-Type": "application/json",
      },
    }
  );
  if (!result.success) {
    throw result.error;
  }
  return result.result as { organization: OrganizationSummary; ids: string[]; total: number };
}

export async function deleteOrganizationPackages(data: { org_id: string; ids: string[] }) {
  const result = await fetchWithErrorHandling(
    baseURL + "/api/3/action/udc_organization_packages_delete",
    {
      method: "POST",
      body: JSON.stringify(data),
      headers: {
        "Content-Type": "application/json",
      },
    }
  );
  if (!result.success) {
    throw result.error;
  }
  return result.result;
}

export async function listDeletedUsers(params: { page: number; page_size: number; filters?: UserListFilters }) {
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/deleted_users_list", {
    method: "POST",
    body: JSON.stringify(params),
    headers: {
      "Content-Type": "application/json",
    }
  });
  if (!result.success) {
    throw result.error;
  }
  return result.result as UserListResponse;
}

export async function resetUserPassword(data: { id: string; new_password: string }) {
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/udc_user_reset_password", {
    method: "POST",
    body: JSON.stringify(data),
    headers: {
      "Content-Type": "application/json",
    }
  });
  if (!result.success) {
    throw result.error;
  }
  return result.result;
}

export async function deleteUser(data: { id: string }) {
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/udc_user_delete", {
    method: "POST",
    body: JSON.stringify(data),
    headers: {
      "Content-Type": "application/json",
    }
  });
  if (!result.success) {
    throw result.error;
  }
  return result.result;
}

export async function purgeDeletedUsers(data: { ids: string[] }) {
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/purge_deleted_users", {
    method: "POST",
    body: JSON.stringify(data),
    headers: {
      "Content-Type": "application/json",
    }
  });
  if (!result.success) {
    throw result.error;
  }
  return result.result;
}

export async function getLicenses(): Promise<License[]> {
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/licenses_get");
  return result.result;
}

export async function createLicense(data: {id: string, title: string, url: string}) {
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/license_create", {
    method: "POST",
    body: JSON.stringify(data),
    headers: {
      "Content-Type": "application/json",
    }
  });
  if (!result.success) {
    throw result.error;
  }
  return result.result;
}

export async function deleteLicense(data: {id: string}) {
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/license_delete", {
    method: "POST",
    body: JSON.stringify(data),
    headers: {
      "Content-Type": "application/json",
    }
  });
  if (!result.success) {
    throw result.error;
  }
  return result.result;
}

export async function updateLicense(data: {id: string, title: string, url: string}) {
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/license_update", {
    method: "POST",
    body: JSON.stringify(data),
    headers: {
      "Content-Type": "application/json",
    }
  });
  if (!result.success) {
    throw result.error;
  }
  return result.result;
}

export async function reloadSupervisor(task: string) {
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/reload_supervisord", {
    method: "POST",
    body: JSON.stringify({ task }),
    headers: {
      "Content-Type": "application/json",
    }
  });
  if (!result.success) {
    throw result.error;
  }
  return result.result;
}

export async function getSystemStats() {
  const result = await fetchWithErrorHandling(baseURL + "/api/3/action/get_system_stats");
  return result.result;
}
