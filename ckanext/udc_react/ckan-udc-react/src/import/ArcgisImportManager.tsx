import { useEffect, useMemo, useState } from "react";
import {
  Box,
  Button,
  Container,
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import CodeMirror from "@uiw/react-codemirror";
import { json } from "@codemirror/lang-json";
import {
  DataGrid,
  GridColDef,
  GridRenderCellParams,
  GridRowSelectionModel,
} from "@mui/x-data-grid";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import HistoryIcon from "@mui/icons-material/History";
import CloseIcon from "@mui/icons-material/Close";
import RefreshIcon from "@mui/icons-material/Refresh";
import DataObjectOutlined from "@mui/icons-material/DataObjectOutlined";
import WarningAmberOutlinedIcon from "@mui/icons-material/WarningAmberOutlined";
import { useApi } from "../api/useApi";
import ErrorDialog from "../udrc/License/ErrorDialog";
import ImportPanel from "./ImportPanel";
import PortalDetailsDialog from "./components/PortalDetailsDialog";
import { CKANOrganization, ImportConfig } from "../api/api";
import { formatLocalTimestamp } from "./utils/time";

const ArcgisImportManager = () => {
  const { api, executeApiCall } = useApi();
  const [configs, setConfigs] = useState<ImportConfig[]>([]);
  const [organizations, setOrganizations] = useState<CKANOrganization[]>([]);
  const [loading, setLoading] = useState(false);
  const [runLoading, setRunLoading] = useState(false);
  const [selectionModel, setSelectionModel] = useState<GridRowSelectionModel>([]);
  const [error, setError] = useState<string | null>(null);
  const [errorDialogOpen, setErrorDialogOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<ImportConfig | null>(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [portalDialogOpen, setPortalDialogOpen] = useState(false);
  const [portalTarget, setPortalTarget] = useState<ImportConfig | null>(null);
  const [rawDialogOpen, setRawDialogOpen] = useState(false);
  const [rawTarget, setRawTarget] = useState<ImportConfig | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ImportConfig | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [statusDialogOpen, setStatusDialogOpen] = useState(false);
  const [statusTarget, setStatusTarget] = useState<ImportConfig | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);
  const [statusLogs, setStatusLogs] = useState<any[]>([]);
  const [query, setQuery] = useState("");
  const [columnVisibilityModel, setColumnVisibilityModel] = useState({
    discoverable: false,
    updated_at: false,
  });

  const load = async () => {
    setLoading(true);
    try {
      const [configResult, orgs] = await Promise.all([
        executeApiCall(() => api.getArcgisAutoImportConfigs()),
        executeApiCall(api.getOrganizations),
      ]);
      setConfigs(configResult.results ?? []);
      setOrganizations(orgs ?? []);
    } catch (err) {
      setError("Failed to load ArcGIS import configs.");
      setErrorDialogOpen(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const selectedConfigIds = useMemo(() => {
    if (!selectionModel.length) {
      return [];
    }
    const ids = new Set(selectionModel.map((value) => String(value)));
    return configs
      .filter((config) => ids.has(config.id))
      .map((config) => config.id);
  }, [configs, selectionModel]);

  const getPortalSnapshot = (config: ImportConfig) => {
    return config.portal_snapshot ?? (config.other_data as Record<string, unknown> | undefined)?.portal_snapshot;
  };

  const getPortalDetails = (config: ImportConfig | null) => {
    if (!config) {
      return null;
    }
    const snapshot = getPortalSnapshot(config) as Record<string, unknown> | undefined;
    if (snapshot) {
      return snapshot;
    }
    const other = getOtherConfig(config);
    return {
      id: (other.portal_id as string) ?? config.owner_org ?? "",
      title: (other.portal_title as string) ?? config.name ?? "",
      url: (other.portal_url as string) ?? "",
      orgId: (other.portal_org_id as string) ?? "",
      portalName: (other.portal_name as string) ?? "",
      description: (other.portal_description as string) ?? config.notes ?? "",
    };
  };

  const getPortalRaw = (config: ImportConfig | null) => {
    if (!config) {
      return {};
    }
    const snapshot = getPortalSnapshot(config) as Record<string, unknown> | undefined;
    if (snapshot && typeof snapshot === "object" && "raw" in snapshot) {
      return (snapshot as Record<string, unknown>).raw ?? {};
    }
    return snapshot ?? {};
  };

  const getOtherConfig = (config: ImportConfig) => {
    return (config.other_config || {}) as Record<string, unknown>;
  };

  const getOrganization = (config: ImportConfig) => {
    const ownerOrg = config.owner_org;
    if (!ownerOrg) {
      return undefined;
    }
    return organizations.find(
      (org) => org.id === ownerOrg || org.name === ownerOrg
    );
  };

  const filteredConfigs = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) {
      return configs;
    }
    return configs.filter((config) => {
      const snapshot = getPortalSnapshot(config) as Record<string, unknown> | undefined;
      const other = getOtherConfig(config);
      const org = getOrganization(config);
      const values = [
        config.name,
        config.notes,
        String(other.portal_title ?? ""),
        String(other.portal_url ?? ""),
        String(other.portal_id ?? ""),
        String(other.base_api ?? ""),
        String(snapshot?.title ?? ""),
        String(snapshot?.url ?? ""),
        String(snapshot?.orgId ?? ""),
        org?.display_name,
        org?.title,
        org?.name,
        config.owner_org,
      ];
      return values.some((value) => (value ?? "").toString().toLowerCase().includes(normalized));
    });
  }, [configs, getOrganization, query]);

  const getImportedCount = (config: ImportConfig) => {
    const otherData = (config.other_data || {}) as Record<string, unknown>;
    const importedMap = otherData.imported_id_map as Record<string, unknown> | undefined;
    if (importedMap && typeof importedMap === "object") {
      return Object.keys(importedMap).length;
    }
    const importedIds = otherData.imported_ids as string[] | undefined;
    if (Array.isArray(importedIds)) {
      return importedIds.length;
    }
    return 0;
  };

  const getDatasetCount = (config: ImportConfig) => {
    const snapshot = getPortalSnapshot(config) as Record<string, unknown> | undefined;
    const rawCount =
      config.datasetCount ??
      (snapshot?.datasetCount as number | string | undefined) ??
      (snapshot?.dataset_count as number | string | undefined);
    if (rawCount == null) {
      return null;
    }
    const parsed = Number(rawCount);
    return Number.isFinite(parsed) ? parsed : null;
  };

  const formatCount = (value: number | null): string => {
    if (value == null) {
      return "-";
    }
    return String(value);
  };

  const handleRunSelected = async () => {
    if (!selectedConfigIds.length) {
      return;
    }
    setRunLoading(true);
    try {
      for (const configId of selectedConfigIds) {
        await executeApiCall(() => api.runImport(configId));
      }
    } catch (err) {
      setError("Failed to run selected imports.");
      setErrorDialogOpen(true);
    } finally {
      setRunLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) {
      return;
    }
    setDeleteLoading(true);
    try {
      const result = await executeApiCall(() =>
        api.deleteArcgisAutoImportConfigs({ config_ids: [deleteTarget.id] })
      );
      if (result.blocked?.length) {
        const blocked = result.blocked[0];
        const reason = blocked.reason
          ? ` ${blocked.reason}`
          : `Cannot delete while ${blocked.imported_count ?? "some"} imported datasets remain. Clear the import for organization ${blocked.owner_org || "unknown"} first.`;
        setError(reason);
        setErrorDialogOpen(true);
        return;
      }
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
      setSelectionModel([]);
      await load();
    } catch (err) {
      setError("Failed to delete ArcGIS import config.");
      setErrorDialogOpen(true);
    } finally {
      setDeleteLoading(false);
    }
  };

  const handleOpenStatus = async (config: ImportConfig) => {
    setStatusTarget(config);
    setStatusDialogOpen(true);
    setStatusLoading(true);
    try {
      const logs = await executeApiCall(() => api.getImportLogsByConfigId(config.id));
      const list = Array.isArray(logs) ? logs : [];
      list.sort((a, b) => {
        const aTime = new Date(a.run_at || 0).getTime();
        const bTime = new Date(b.run_at || 0).getTime();
        return bTime - aTime;
      });
      setStatusLogs(list);
    } catch (err) {
      setStatusLogs([]);
      setError("Failed to load import status logs.");
      setErrorDialogOpen(true);
    } finally {
      setStatusLoading(false);
    }
  };

  const summarizeFinished = (log: any) => {
    const finished = log?.other_data?.finished;
    if (!Array.isArray(finished)) {
      return null;
    }
    const counts = {
      created: 0,
      updated: 0,
      deleted: 0,
      errored: 0,
    };
    finished.forEach((item) => {
      const type = String(item?.type || "");
      if (type in counts) {
        counts[type as keyof typeof counts] += 1;
      }
    });
    return counts;
  };

  const columns = useMemo<GridColDef<ImportConfig>[]>(
    () => [
      {
        field: "name",
        headerName: "Import Name",
        flex: 1,
        minWidth: 220,
        renderCell: (params: GridRenderCellParams<ImportConfig>) => (
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            {params.row?.discoverable === false ? (
              <Tooltip title="No longer discoverable">
                <WarningAmberOutlinedIcon fontSize="small" color="warning" />
              </Tooltip>
            ) : null}
            <Typography variant="body2">{params.row?.name || "-"}</Typography>
          </Box>
        ),
      },
      {
        field: "portalTitle",
        headerName: "Portal",
        flex: 1,
        minWidth: 220,
        valueGetter: (_value: unknown, row: ImportConfig) => {
          const safeRow = row ?? ({} as ImportConfig);
          const snapshot = getPortalSnapshot(row) as Record<string, unknown> | undefined;
          return (
            (getOtherConfig(safeRow).portal_title as string) ||
            (snapshot?.title as string) ||
            safeRow.name
          );
        },
      },
      {
        field: "portalUrl",
        headerName: "Portal URL",
        flex: 1.4,
        minWidth: 260,
        renderCell: (params: GridRenderCellParams<ImportConfig>) => {
          const snapshot = getPortalSnapshot(params.row) as Record<string, unknown> | undefined;
          const url =
            (getOtherConfig(params.row).portal_url as string) ||
            (snapshot?.url as string) ||
            "-";
          return url && url !== "-" ? (
            <a href={url} target="_blank" rel="noopener noreferrer">
              {url}
            </a>
          ) : (
            <Typography variant="body2">-</Typography>
          );
        },
      },
      {
        field: "organization",
        headerName: "Organization",
        minWidth: 220,
        renderCell: (params: GridRenderCellParams<ImportConfig>) => {
          const org = getOrganization(params.row);
          const label = org?.display_name || org?.title || org?.name || params.row?.owner_org || "-";
          return org?.name ? (
            <a href={`/organization/${org.name}`} target="_blank" rel="noopener noreferrer">
              {label}
            </a>
          ) : (
            <Typography variant="body2">{label}</Typography>
          );
        },
      },
      {
        field: "discoverable",
        headerName: "Discovery",
        minWidth: 200,
        renderCell: (params: GridRenderCellParams<ImportConfig>) => {
          if (params.row?.discoverable === false) {
            return (
              <Typography variant="body2" color="warning.main">
                No longer discoverable
              </Typography>
            );
          }
          return <Typography variant="body2">-</Typography>;
        },
      },
      {
        field: "portalId",
        headerName: "Portal ID",
        minWidth: 220,
        valueGetter: (_value: unknown, row: ImportConfig) => getOtherConfig(row ?? {}).portal_id as string,
      },
      {
        field: "baseApi",
        headerName: "Base API",
        minWidth: 220,
        valueGetter: (_value: unknown, row: ImportConfig) => getOtherConfig(row ?? {}).base_api as string,
      },
      {
        field: "updated_at",
        headerName: "Last Updated",
        minWidth: 180,
        valueGetter: (_value: unknown, row: ImportConfig) => row?.updated_at || "",
      },
      {
        field: "imported_count",
        headerName: "Imported",
        minWidth: 110,
        valueGetter: (_value: unknown, row: ImportConfig) => getImportedCount(row ?? ({} as ImportConfig)),
      },
      {
        field: "last_run_at",
        headerName: "Last Run",
        minWidth: 190,
        valueGetter: (_value: unknown, row: ImportConfig) => row?.last_run_at || "",
        renderCell: (params: GridRenderCellParams<ImportConfig>) => (
          <Typography variant="body2">
            {formatLocalTimestamp(params.row?.last_run_at ?? null)}
          </Typography>
        ),
      },
      {
        field: "datasetCount",
        headerName: "Datasets",
        minWidth: 110,
        valueGetter: (_value: unknown, row: ImportConfig) => getDatasetCount(row ?? ({} as ImportConfig)),
        renderCell: (params: GridRenderCellParams<ImportConfig>) => (
          <Box>
            <Typography variant="body2">
              {formatCount(getDatasetCount(params.row ?? ({} as ImportConfig)))}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
              {formatLocalTimestamp(params.row?.countsUpdatedAt ?? null)}
            </Typography>
          </Box>
        ),
      },
      {
        field: "actions",
        headerName: "Actions",
        minWidth: 280,
        renderCell: (params: GridRenderCellParams<ImportConfig>) => (
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Tooltip title="Edit import config">
              <IconButton
                size="small"
                aria-label="Edit import config"
                onClick={() => {
                  setEditTarget(params.row);
                  setEditDialogOpen(true);
                }}
              >
                <EditOutlinedIcon fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title="Portal details">
              <IconButton
                size="small"
                aria-label="Portal details"
                onClick={() => {
                  setPortalTarget(params.row);
                  setPortalDialogOpen(true);
                }}
              >
                <InfoOutlinedIcon fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title="Raw JSON">
              <IconButton
                size="small"
                aria-label="Raw JSON"
                onClick={() => {
                  setRawTarget(params.row);
                  setRawDialogOpen(true);
                }}
              >
                <DataObjectOutlined fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title="Last import status">
              <IconButton
                size="small"
                aria-label="Last import status"
                onClick={() => handleOpenStatus(params.row)}
              >
                <HistoryIcon fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title="Delete import config">
              <IconButton
                size="small"
                color="error"
                aria-label="Delete import config"
                onClick={() => {
                  setDeleteTarget(params.row);
                  setDeleteDialogOpen(true);
                }}
              >
                <DeleteOutlineIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Box>
        ),
      },
    ],
    [organizations]
  );

  return (
    <Container maxWidth={false} disableGutters sx={{ width: "100%" }}>
      <Typography variant="h5" paddingBottom={2}>
        ArcGIS Auto Imports
      </Typography>
      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2, flexWrap: "wrap" }}>
        <Tooltip title="Refresh">
          <span>
            <IconButton aria-label="Refresh" onClick={load} disabled={loading} size="small">
              <RefreshIcon fontSize="small" />
            </IconButton>
          </span>
        </Tooltip>
        <TextField
          label="Filter"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          size="small"
          sx={{ minWidth: 240 }}
        />
        <Button
          variant="contained"
          onClick={handleRunSelected}
          disabled={runLoading || selectedConfigIds.length === 0}
        >
          {runLoading ? "Running..." : `Run Selected (${selectedConfigIds.length})`}
        </Button>
      </Box>
      <Box sx={{ height: 680, width: "100%" }}>
        <DataGrid<ImportConfig>
          rows={filteredConfigs}
          columns={columns}
          getRowId={(row) => row.id}
          checkboxSelection
          rowSelectionModel={selectionModel}
          onRowSelectionModelChange={setSelectionModel}
          columnVisibilityModel={columnVisibilityModel}
          onColumnVisibilityModelChange={setColumnVisibilityModel}
          loading={loading}
          disableRowSelectionOnClick
          pageSizeOptions={[10, 25, 50, 100]}
        />
      </Box>

      <ErrorDialog
        open={errorDialogOpen}
        onClose={() => setErrorDialogOpen(false)}
        error={error || "Unexpected error"}
      />

      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="lg" fullWidth>
        <DialogTitle sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", pr: 1 }}>
          <span>Edit Import Config</span>
          <Tooltip title="Close">
            <IconButton aria-label="Close" onClick={() => setEditDialogOpen(false)} size="small">
              <CloseIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </DialogTitle>
        <DialogContent>
          {editTarget ? (
            <ImportPanel
              defaultConfig={{ uuid: editTarget.id, ...editTarget }}
              onUpdate={() => {
                setEditDialogOpen(false);
                load();
              }}
              organizations={organizations}
            />
          ) : null}
        </DialogContent>
      </Dialog>

      <PortalDetailsDialog
        open={portalDialogOpen}
        onClose={() => setPortalDialogOpen(false)}
        portal={getPortalDetails(portalTarget)}
      />

      <Dialog open={rawDialogOpen} onClose={() => setRawDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", pr: 1 }}>
          <span>Portal Raw JSON</span>
          <Tooltip title="Close">
            <IconButton aria-label="Close" onClick={() => setRawDialogOpen(false)} size="small">
              <CloseIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </DialogTitle>
        <DialogContent>
          <CodeMirror
            value={JSON.stringify(getPortalRaw(rawTarget), null, 2)}
            extensions={[json()]}
            readOnly
            basicSetup={{ lineNumbers: true, foldGutter: false }}
            style={{ fontSize: 12 }}
          />
        </DialogContent>
      </Dialog>

      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", pr: 1 }}>
          <span>Delete Import Config</span>
          <Tooltip title="Close">
            <IconButton aria-label="Close" onClick={() => setDeleteDialogOpen(false)} size="small">
              <CloseIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 2 }}>
            This will remove the auto-generated import config for{" "}
            <strong>{deleteTarget?.name ?? "this portal"}</strong>. It will also clear the
            configured status in ArcGIS Portal Discovery after refresh.
          </Typography>
          <Box sx={{ display: "flex", justifyContent: "flex-end", gap: 1 }}>
            <Button variant="outlined" onClick={() => setDeleteDialogOpen(false)} disabled={deleteLoading}>
              Cancel
            </Button>
            <Button variant="contained" color="error" onClick={handleDelete} disabled={deleteLoading}>
              {deleteLoading ? "Deleting..." : "Delete"}
            </Button>
          </Box>
        </DialogContent>
      </Dialog>

      <Dialog open={statusDialogOpen} onClose={() => setStatusDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", pr: 1 }}>
          <span>Last Import Status</span>
          <Tooltip title="Close">
            <IconButton aria-label="Close" onClick={() => setStatusDialogOpen(false)} size="small">
              <CloseIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </DialogTitle>
        <DialogContent>
          <Typography variant="subtitle2" sx={{ mb: 2 }}>
            {statusTarget?.name ?? "Import config"}
          </Typography>
          <Typography variant="body2" sx={{ mb: 2 }}>
            <a
              href={`/udrc/import-status?configId=${encodeURIComponent(statusTarget?.id || "")}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              View full import status
            </a>
          </Typography>
          {statusLoading ? (
            <Typography variant="body2">Loading status logs...</Typography>
          ) : statusLogs.length === 0 ? (
            <Typography variant="body2">No import logs found.</Typography>
          ) : (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              {statusLogs.map((log) => (
                <Box
                  key={log.id}
                  sx={{
                    border: "1px solid",
                    borderColor: "divider",
                    borderRadius: 1,
                    p: 2,
                  }}
                >
                  <Typography variant="body2">
                    Run at: {log.run_at ? new Date(log.run_at).toLocaleString() : "-"}
                  </Typography>
                  <Typography variant="body2">Status: {log.has_error ? "Error" : log.has_warning ? "Warning" : "OK"}</Typography>
                  <Typography variant="body2">Log ID: {log.id}</Typography>
                  {summarizeFinished(log) ? (
                    <Typography variant="body2" sx={{ mt: 1 }}>
                      Finished: {summarizeFinished(log)?.created ?? 0} created,{" "}
                      {summarizeFinished(log)?.updated ?? 0} updated,{" "}
                      {summarizeFinished(log)?.deleted ?? 0} deleted,{" "}
                      {summarizeFinished(log)?.errored ?? 0} errored
                    </Typography>
                  ) : null}
                  {log.logs ? (
                    <Box sx={{ mt: 1 }}>
                      <Typography variant="caption" color="text.secondary">
                        Logs preview
                      </Typography>
                      <Box
                        component="pre"
                        sx={{
                          mt: 0.5,
                          p: 1,
                          borderRadius: 1,
                          border: "1px solid",
                          borderColor: "divider",
                          maxHeight: 140,
                          overflow: "auto",
                          fontSize: 12,
                          whiteSpace: "pre-wrap",
                        }}
                      >
                        {String(log.logs).split("\n").slice(0, 12).join("\n")}
                      </Box>
                    </Box>
                  ) : null}
                </Box>
              ))}
            </Box>
          )}
        </DialogContent>
      </Dialog>
    </Container>
  );
};

export default ArcgisImportManager;
