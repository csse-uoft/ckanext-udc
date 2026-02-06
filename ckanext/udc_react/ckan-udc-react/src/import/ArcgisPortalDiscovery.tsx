import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Box,
  Button,
  Chip,
  Checkbox,
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
  FormControlLabel,
  Divider,
  LinearProgress,
  Menu,
  MenuItem,
  Switch,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import {
  DataGrid,
  GridColDef,
  GridPaginationModel,
  GridRenderCellParams,
  GridRowSelectionModel,
  GridSortModel,
} from "@mui/x-data-grid";
import { useApi } from "../api/useApi";
import ErrorDialog from "../udrc/License/ErrorDialog";
import { ArcgisPortalCandidate, ArcgisPortalKeywordGroup, ImportConfig } from "../api/api";
import KeywordGroupsDialog from "./components/KeywordGroupsDialog";
import DataObjectOutlined from "@mui/icons-material/DataObjectOutlined";
import InfoOutlined from "@mui/icons-material/InfoOutlined";
import RefreshIcon from "@mui/icons-material/Refresh";
import CloseIcon from "@mui/icons-material/Close";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import CodeMirror from "@uiw/react-codemirror";
import { json } from "@codemirror/lang-json";
import { formatLocalTimestamp } from "./utils/time";
import PortalDetailsDialog from "./components/PortalDetailsDialog";

const ArcgisPortalDiscovery: React.FC = () => {
  const { api, executeApiCall } = useApi();
  const [results, setResults] = useState<ArcgisPortalCandidate[]>([]);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const arcgisRoot = "https://www.arcgis.com";
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [configLoading, setConfigLoading] = useState(false);
  const [configSaving, setConfigSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorDialogOpen, setErrorDialogOpen] = useState(false);
  const [countsLoading, setCountsLoading] = useState(false);
  // Accurate counts scan all datasets and apply import filters; fast counts use API totals only.
  const [countMode, setCountMode] = useState<"fast" | "accurate">("accurate");
  const [countsProgress, setCountsProgress] = useState<{
    total: number;
    completed: number;
    failed: number;
  } | null>(null);
  const [countsMenuAnchorEl, setCountsMenuAnchorEl] = useState<null | HTMLElement>(null);
  const [rawDialogOpen, setRawDialogOpen] = useState(false);
  const [rawTarget, setRawTarget] = useState<ArcgisPortalCandidate | null>(null);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [detailTarget, setDetailTarget] = useState<ArcgisPortalCandidate | null>(null);
  const [keywordDialogOpen, setKeywordDialogOpen] = useState(false);
  const [sortModel, setSortModel] = useState<GridSortModel>([]);
  const [keywordGroups, setKeywordGroups] = useState<ArcgisPortalKeywordGroup[]>([]);
  const [defaultKeywordGroups, setDefaultKeywordGroups] = useState<ArcgisPortalKeywordGroup[]>([]);
  const [termInputs, setTermInputs] = useState<Record<number, string>>({});
  const termInputsRef = useRef<Record<number, string>>({});
  const [keywordGroupsUpdatedAt, setKeywordGroupsUpdatedAt] = useState<string | null>(null);
  const [autoConfigs, setAutoConfigs] = useState<ImportConfig[]>([]);
  const [selectionModel, setSelectionModel] = useState<GridRowSelectionModel>([]);
  const [createLoading, setCreateLoading] = useState(false);
  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({
    page: 0,
    pageSize: 25,
  });
  const [columnVisibilityModel, setColumnVisibilityModel] = useState({
    portalName: false,
    orgId: false,
  });
  const [hideZeroDatasets, setHideZeroDatasets] = useState(false);
  const [hideNoMatches, setHideNoMatches] = useState(false);

  const asList = (value: unknown): string[] => {
    if (Array.isArray(value)) {
      return value.map((item) => String(item));
    }
    if (value == null) {
      return [];
    }
    return [String(value)];
  };

  const formatValue = (value: unknown): string => {
    if (value == null || value === "") {
      return "-";
    }
    if (Array.isArray(value)) {
      return value.map((item) => String(item)).join(", ") || "-";
    }
    return String(value);
  };

  const formatDate = (value: unknown): string => {
    if (value == null || value === "") {
      return "-";
    }
    if (typeof value === "number") {
      return new Date(value).toLocaleString();
    }
    if (typeof value === "string") {
      const parsed = Number(value);
      if (!Number.isNaN(parsed)) {
        return new Date(parsed).toLocaleString();
      }
    }
    return String(value);
  };

  const renderHtml = (value?: string | null) => ({
    __html: value ?? "",
  });

  const renderTooltipHtml = (value?: string | null) => (
    <Box sx={{ maxWidth: 360 }} dangerouslySetInnerHTML={renderHtml(value)} />
  );

  const renderTagChips = (values: string[]) => (
    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
      {values.map((value) => (
        <Chip key={value} size="small" label={value} />
      ))}
    </Box>
  );

  const tooltipSlotProps = {
    tooltip: {
      sx: {
        bgcolor: "background.paper",
        color: "text.primary",
        border: "1px solid",
        borderColor: "divider",
        boxShadow: 2,
      },
    },
    arrow: {
      sx: {
        color: "background.paper",
      },
    },
  };

  const TagChipsCell: React.FC<{ values: string[] }> = ({ values }) => {
    const containerRef = useRef<HTMLDivElement | null>(null);
    const [visibleCount, setVisibleCount] = useState(3);

    useEffect(() => {
      const element = containerRef.current;
      if (!element) {
        return;
      }
      const update = () => {
        const width = element.offsetWidth;
        if (!width) {
          return;
        }
        const chipMinWidth = 72;
        const maxVisible = Math.max(1, Math.floor(width / chipMinWidth));
        setVisibleCount(Math.min(values.length, maxVisible));
      };
      update();
      const observer = new ResizeObserver(update);
      observer.observe(element);
      return () => observer.disconnect();
    }, [values.length]);

    if (values.length === 0) {
      return <Typography variant="body2">-</Typography>;
    }

    const preview = values.slice(0, visibleCount);
    const remaining = values.length - preview.length;

    return (
      <Tooltip title={renderTagChips(values)} arrow slotProps={tooltipSlotProps}>
        <Box ref={containerRef} sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, overflow: "hidden" }}>
          {preview.map((value) => (
            <Chip key={value} size="small" label={value} />
          ))}
          {remaining > 0 ? <Chip size="small" label={`+${remaining}`} /> : null}
        </Box>
      </Tooltip>
    );
  };

  const filteredResults = useMemo(() => {
    let data = results;
    if (query.trim()) {
      const q = query.toLowerCase();
      data = data.filter((item) => {
        return (
          item.title?.toLowerCase().includes(q) ||
          item.url?.toLowerCase().includes(q) ||
          item.portalName?.toLowerCase().includes(q) ||
          item.orgId?.toLowerCase().includes(q) ||
          (item.tags ?? item.raw?.tags ?? []).join(" ").toLowerCase().includes(q) ||
          (item.matchedTerms ?? []).join(" ").toLowerCase().includes(q) ||
          (item.matchReasons ?? item.matchedTerms ?? []).join(" ").toLowerCase().includes(q)
        );
      });
    }
    if (hideNoMatches) {
      data = data.filter((item) => (item.matchedTerms ?? []).length > 0);
    }
    return data;
  }, [hideNoMatches, query, results]);

  const filteredResultsWithCounts = useMemo(() => {
    const countsAvailable = results.some((row) => row.datasetCount != null);
    if (!hideZeroDatasets || !countsAvailable) {
      return filteredResults;
    }
    return filteredResults.filter((row) => {
      const value = row.datasetCount;
      if (value == null) {
        return true;
      }
      const parsed = Number(value);
      return !Number.isFinite(parsed) || parsed > 0;
    });
  }, [filteredResults, hideZeroDatasets, results]);

  const autoConfigByPortalId = useMemo(() => {
    const map = new Map<string, ImportConfig>();
    autoConfigs.forEach((config) => {
      const portalId = config.other_config?.portal_id as string | undefined;
      if (portalId) {
        map.set(portalId, config);
      }
    });
    return map;
  }, [autoConfigs]);

  const selectedPortalIds = useMemo(() => {
    if (!selectionModel.length) {
      return [];
    }
    const selectedIds = new Set(selectionModel.map((value) => String(value)));
    return results
      .filter((row) => selectedIds.has(row.url))
      .map((row) => row.id)
      .filter((id): id is string => Boolean(id));
  }, [results, selectionModel]);

  const selectedRows = useMemo(() => {
    if (!selectionModel.length) {
      return [];
    }
    const selectedIds = new Set(selectionModel.map((value) => String(value)));
    return results.filter((row) => selectedIds.has(row.url));
  }, [results, selectionModel]);

  const missingCountPortalIds = useMemo(() => {
    return selectedRows
      .filter((row) => row.datasetCount == null)
      .map((row) => row.id)
      .filter((id): id is string => Boolean(id));
  }, [selectedRows]);

  const selectedDatasetSummary = useMemo(() => {
    let total = 0;
    let unknown = 0;
    for (const row of selectedRows) {
      const raw = row.datasetCount;
      if (raw == null) {
        unknown += 1;
        continue;
      }
      const parsed = Number(raw);
      if (Number.isFinite(parsed)) {
        total += parsed;
      } else {
        unknown += 1;
      }
    }
    return { total, unknown };
  }, [selectedRows]);

  const getSortValue = (row: ArcgisPortalCandidate, field: string) => {
    switch (field) {
      case "numViews":
        return row.raw?.numViews ?? 0;
      case "lastViewed":
        return row.raw?.lastViewed ?? 0;
      case "modified":
        return row.raw?.modified ?? 0;
      case "culture":
        return row.raw?.culture ?? "";
      case "matchReasons":
        return asList(row.matchReasons ?? row.matchedTerms).join(", ");
      case "tags":
        return asList(row.tags ?? row.raw?.tags).join(", ");
      case "snippet":
        return row.snippet ?? "";
      case "description":
        return row.description ?? "";
      case "portalName":
        return row.portalName ?? "";
      case "orgId":
        return row.orgId ?? "";
      case "importStatus":
        return row.id && autoConfigByPortalId.has(row.id) ? 1 : 0;
      case "url":
        return row.url ?? "";
      case "title":
        return row.title ?? "";
      default:
        return (row as unknown as Record<string, unknown>)[field] ?? "";
    }
  };

  const sortedResults = useMemo(() => {
    if (sortModel.length === 0) {
      return filteredResultsWithCounts;
    }
    const [{ field, sort }] = sortModel;
    const direction = sort === "desc" ? -1 : 1;
    const copy = [...filteredResultsWithCounts];
    copy.sort((a, b) => {
      const av = getSortValue(a, field);
      const bv = getSortValue(b, field);
      if (av == null && bv == null) {
        return 0;
      }
      if (av == null) {
        return 1;
      }
      if (bv == null) {
        return -1;
      }
      if (typeof av === "number" && typeof bv === "number") {
        return (av - bv) * direction;
      }
      return String(av).localeCompare(String(bv)) * direction;
    });
    return copy;
  }, [autoConfigByPortalId, filteredResultsWithCounts, sortModel]);

  const columns = useMemo<GridColDef<ArcgisPortalCandidate>[]>(
    () => [
      {
        field: "title",
        headerName: "Title",
        flex: 1.4,
        minWidth: 220,
        renderCell: (params: GridRenderCellParams<ArcgisPortalCandidate>) => (
          <a href={params.row.url} target="_blank" rel="noopener noreferrer">
            {params.value}
          </a>
        ),
      },
      {
        field: "actions",
        headerName: "Details",
        width: 120,
        sortable: false,
        filterable: false,
        renderCell: (params: GridRenderCellParams<ArcgisPortalCandidate>) => (
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Tooltip title="Portal details">
              <IconButton
                size="small"
                onClick={() => {
                  setDetailTarget(params.row);
                  setDetailDialogOpen(true);
                }}
              >
                <InfoOutlined fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title="Raw JSON">
              <IconButton
                size="small"
                onClick={() => {
                  setRawTarget(params.row);
                  setRawDialogOpen(true);
                }}
              >
                <DataObjectOutlined fontSize="small" />
              </IconButton>
            </Tooltip>
          </Box>
        ),
      },
      {
        field: "importStatus",
        headerName: "Import",
        width: 140,
        valueGetter: (_value: unknown, row: ArcgisPortalCandidate) => {
          const portalId = row?.id;
          return portalId && autoConfigByPortalId.has(portalId) ? 1 : 0;
        },
        sortComparator: (v1, v2) => Number(v1 ?? 0) - Number(v2 ?? 0),
        renderCell: (params: GridRenderCellParams<ArcgisPortalCandidate>) => {
          const portalId = params.row.id;
          const config = portalId ? autoConfigByPortalId.get(portalId) : undefined;
          if (!config) {
            return <Typography variant="body2">-</Typography>;
          }
          return <Chip size="small" color="success" label="Configured" title={config.name} />;
        },
      },
      { field: "portalName", headerName: "Portal", flex: 1, minWidth: 180 },
      { field: "orgId", headerName: "Org ID", flex: 1, minWidth: 160 },
      {
        field: "datasetCount",
        headerName: "Datasets",
        width: 120,
        valueGetter: (_value: unknown, row: ArcgisPortalCandidate) => row?.datasetCount ?? null,
        sortComparator: (v1, v2) => Number(v1 ?? 0) - Number(v2 ?? 0),
        renderCell: (params: GridRenderCellParams<ArcgisPortalCandidate>) => (
          <Box>
            <Typography variant="body2">{formatValue(params.row?.datasetCount)}</Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
              {formatLocalTimestamp(params.row?.countsUpdatedAt ?? null)}
            </Typography>
          </Box>
        ),
      },
      {
        field: "numViews",
        headerName: "Views",
        width: 110,
        valueGetter: (_value: unknown, row: ArcgisPortalCandidate) => row?.raw?.numViews ?? 0,
        sortComparator: (v1, v2) => Number(v1) - Number(v2),
        renderCell: (params: GridRenderCellParams<ArcgisPortalCandidate>) => (
          <Typography variant="body2">{formatValue(params.row?.raw?.numViews)}</Typography>
        ),
      },
      {
        field: "lastViewed",
        headerName: "Last Viewed",
        minWidth: 170,
        valueGetter: (_value: unknown, row: ArcgisPortalCandidate) => row?.raw?.lastViewed ?? 0,
        sortComparator: (v1, v2) => Number(v1) - Number(v2),
        renderCell: (params: GridRenderCellParams<ArcgisPortalCandidate>) => (
          <Typography variant="body2">{formatDate(params.row?.raw?.lastViewed)}</Typography>
        ),
      },
      {
        field: "modified",
        headerName: "Modified",
        minWidth: 170,
        valueGetter: (_value: unknown, row: ArcgisPortalCandidate) => row?.raw?.modified ?? 0,
        sortComparator: (v1, v2) => Number(v1) - Number(v2),
        renderCell: (params: GridRenderCellParams<ArcgisPortalCandidate>) => (
          <Typography variant="body2">{formatDate(params.row?.raw?.modified)}</Typography>
        ),
      },
      {
        field: "culture",
        headerName: "Culture",
        width: 120,
        valueGetter: (_value: unknown, row: ArcgisPortalCandidate) => row?.raw?.culture ?? "",
        renderCell: (params: GridRenderCellParams<ArcgisPortalCandidate>) => (
          <Typography variant="body2">{formatValue(params.row?.raw?.culture)}</Typography>
        ),
      },
      {
        field: "matchReasons",
        headerName: "Match Reasons",
        flex: 1.4,
        minWidth: 260,
        renderCell: (params: GridRenderCellParams<ArcgisPortalCandidate>) => {
          const values = asList(params.row?.matchReasons ?? params.row?.matchedTerms);
          return <TagChipsCell values={values} />;
        },
      },
      {
        field: "tags",
        headerName: "Tags",
        flex: 1.2,
        minWidth: 200,
        renderCell: (params: GridRenderCellParams<ArcgisPortalCandidate>) => {
          const values = asList(params.row?.tags ?? params.row?.raw?.tags);
          return <TagChipsCell values={values} />;
        },
      },
      {
        field: "snippet",
        headerName: "Snippet",
        flex: 1.6,
        minWidth: 240,
        renderCell: (params: GridRenderCellParams<ArcgisPortalCandidate>) => {
          const text = (params.value as string) || "";
          return (
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <Tooltip title={renderTooltipHtml(text)} arrow slotProps={tooltipSlotProps}>
                <Box
                  sx={{
                    maxWidth: "100%",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    display: "-webkit-box",
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: "vertical",
                  }}
                  dangerouslySetInnerHTML={renderHtml(text)}
                />
              </Tooltip>
            </Box>
          );
        },
      },
      {
        field: "description",
        headerName: "Description",
        flex: 2,
        minWidth: 280,
        renderCell: (params: GridRenderCellParams<ArcgisPortalCandidate>) => {
          const text = (params.value as string) || "";
          return (
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <Tooltip title={renderTooltipHtml(text)} arrow slotProps={tooltipSlotProps}>
                <Typography
                  variant="body2"
                  sx={{
                    maxWidth: "100%",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    display: "-webkit-box",
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: "vertical",
                  }}
                >
                  {text}
                </Typography>
              </Tooltip>
            </Box>
          );
        },
      },
      {
        field: "url",
        headerName: "URL",
        flex: 1.5,
        minWidth: 280,
      },
    ],
    [autoConfigByPortalId]
  );

  const handleDiscover = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await executeApiCall(() =>
        api.discoverArcgisPortals({
          arcgis_root: arcgisRoot,
        })
      );
      setResults(result.results || []);
      setLastUpdated(result.updated_at ?? null);
      setPaginationModel((prev) => ({ ...prev, page: 0 }));
    } catch (err) {
      setError("Failed to discover ArcGIS portals.");
      setErrorDialogOpen(true);
    } finally {
      setLoading(false);
    }
  };

  const uniqTerms = (values: string[]) => {
    const seen = new Set<string>();
    const result: string[] = [];
    for (const value of values) {
      if (!value) {
        continue;
      }
      const trimmed = value.trim();
      if (!trimmed || seen.has(trimmed)) {
        continue;
      }
      seen.add(trimmed);
      result.push(trimmed);
    }
    return result;
  };

  useEffect(() => {
    termInputsRef.current = termInputs;
  }, [termInputs]);

  const handleTermInputChange = useCallback((index: number, value: string) => {
    setTermInputs((prev) => ({ ...prev, [index]: value }));
  }, []);

  const handleAddTerm = useCallback((index: number) => {
    const raw = termInputsRef.current[index] ?? "";
    const newTerms = uniqTerms(
      raw
        .split(",")
        .map((term) => term.trim())
        .filter((term) => term.length > 0)
    );
    if (newTerms.length === 0) {
      return;
    }
    setKeywordGroups((prev) =>
      prev.map((group, idx) =>
        idx === index
          ? { ...group, terms: uniqTerms([...(group.terms ?? []), ...newTerms]) }
          : group
      )
    );
    setTermInputs((prev) => ({ ...prev, [index]: "" }));
  }, []);

  const handleRemoveTerm = useCallback((index: number, term: string) => {
    setKeywordGroups((prev) =>
      prev.map((group, idx) =>
        idx === index ? { ...group, terms: group.terms.filter((item) => item !== term) } : group
      )
    );
  }, []);

  const handleGroupLabelChange = useCallback((index: number, value: string) => {
    setKeywordGroups((prev) =>
      prev.map((group, idx) => (idx === index ? { ...group, label: value } : group))
    );
  }, []);

  const handleRemoveGroup = useCallback((index: number) => {
    setKeywordGroups((prev) => prev.filter((_, idx) => idx !== index));
    setTermInputs((prev) => {
      const next = { ...prev };
      delete next[index];
      return next;
    });
  }, []);

  const handleAddGroup = useCallback(() => {
    setKeywordGroups((prev) => [...prev, { label: "new-group", terms: [] }]);
  }, []);

  const handleSaveKeywordGroups = async () => {
    if (keywordGroups.length === 0) {
      setError("Add at least one keyword group.");
      setErrorDialogOpen(true);
      return;
    }

    setConfigSaving(true);
    setError(null);
    try {
      const result = await executeApiCall(() =>
        api.updateArcgisPortalDiscoveryConfig({
          keyword_groups: keywordGroups,
        })
      );
      const groups = result.keyword_groups ?? [];
      setKeywordGroups(groups);
      setDefaultKeywordGroups(groups);
      setKeywordGroupsUpdatedAt(result.updated_at ?? null);
    } catch (err) {
      setError("Failed to save keyword groups.");
      setErrorDialogOpen(true);
    } finally {
      setConfigSaving(false);
    }
  };

  const handleResetKeywordGroups = () => {
    setKeywordGroups(defaultKeywordGroups);
    setTermInputs({});
  };

  const handleResetToDefaultGroups = async () => {
    setConfigLoading(true);
    setError(null);
    try {
      const result = await executeApiCall(() => api.getArcgisPortalDiscoveryConfigDefault());
      setKeywordGroups(result.keyword_groups ?? []);
      setTermInputs({});
    } catch (err) {
      setError("Failed to load default keyword groups.");
      setErrorDialogOpen(true);
    } finally {
      setConfigLoading(false);
    }
  };

  const loadAutoConfigs = async () => {
    try {
      const result = await executeApiCall(() => api.getArcgisAutoImportConfigs());
      setAutoConfigs(result.results ?? []);
    } catch (err) {
      setError("Failed to load ArcGIS auto-import configs.");
      setErrorDialogOpen(true);
    }
  };

  const handleCreateImports = async () => {
    if (!selectedPortalIds.length) {
      return;
    }
    setCreateLoading(true);
    setError(null);
    try {
      await handleFindCounts(selectedPortalIds);
      const result = await executeApiCall(() =>
        api.createArcgisAutoImportConfigs({ portal_ids: selectedPortalIds })
      );
      if (result.errors?.length) {
        setError(
          `Some portals failed: ${result.errors.map(([id, msg]) => `${id}: ${msg}`).join("; ")}`
        );
        setErrorDialogOpen(true);
      }
      await loadAutoConfigs();
    } catch (err) {
      setError("Failed to create import configs.");
      setErrorDialogOpen(true);
    } finally {
      setCreateLoading(false);
    }
  };

  const handleFindCounts = async (portalIds?: string[]) => {
    const targetIds = portalIds ?? selectedPortalIds;
    if (!targetIds.length) {
      return;
    }
    const batchSize = countMode === "accurate" ? 5 : 15;
    setCountsLoading(true);
    setCountsProgress({ total: targetIds.length, completed: 0, failed: 0 });
    setError(null);
    try {
      let completed = 0;
      let failed = 0;
      for (let i = 0; i < targetIds.length; i += batchSize) {
        const batch = targetIds.slice(i, i + batchSize);
        try {
          const result = await executeApiCall(() =>
            api.updateArcgisPortalDiscoveryCounts({ portal_ids: batch, count_mode: countMode })
          );
          setResults(result.results || []);
        } catch (err) {
          failed += batch.length;
        } finally {
          completed += batch.length;
          setCountsProgress({ total: targetIds.length, completed, failed });
        }
      }
      if (failed > 0) {
        setError(`Failed to fetch counts for ${failed} portal${failed === 1 ? "" : "s"}.`);
        setErrorDialogOpen(true);
      }
    } finally {
      setCountsLoading(false);
      setCountsProgress(null);
    }
  };

  const handleCountsMenuOpen = (event: React.MouseEvent<HTMLButtonElement>) => {
    setCountsMenuAnchorEl(event.currentTarget);
  };

  const handleCountsMenuClose = () => {
    setCountsMenuAnchorEl(null);
  };

  const refreshCached = async () => {
    setLoading(true);
    setError(null);
      try {
        const result = await executeApiCall(() => api.getArcgisPortalDiscovery());
        setResults(result.results || []);
        setLastUpdated(result.updated_at ?? null);
        await loadAutoConfigs();
    } catch (err) {
      setError("Failed to load cached discovery results.");
      setErrorDialogOpen(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshCached();
  }, [api, executeApiCall]);

  useEffect(() => {
    setPaginationModel((prev) => ({ ...prev, page: 0 }));
  }, [sortModel]);

  useEffect(() => {
    const loadConfig = async () => {
      setConfigLoading(true);
      try {
        const result = await executeApiCall(() => api.getArcgisPortalDiscoveryConfig());
        const groups = result.keyword_groups ?? [];
        setKeywordGroups(groups);
        setDefaultKeywordGroups(groups);
        setKeywordGroupsUpdatedAt(result.updated_at ?? null);
      } catch (err) {
        setError("Failed to load keyword groups.");
        setErrorDialogOpen(true);
      } finally {
        setConfigLoading(false);
      }
    };

    loadConfig();
  }, [api, executeApiCall]);

  useEffect(() => {
    loadAutoConfigs();
  }, [api, executeApiCall]);

  return (
    <Box sx={{ width: "100%" }}>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "1.2fr 1fr" },
          gap: 2,
          mb: 2,
        }}
      >
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center" }}>
          <Button variant="contained" onClick={handleDiscover} disabled={loading} size="small">
            {loading ? "Discovering..." : "Discover"}
          </Button>
          <Button
            variant="outlined"
            onClick={handleCountsMenuOpen}
            disabled={countsLoading || selectedPortalIds.length === 0}
            size="small"
            endIcon={<ArrowDropDownIcon fontSize="small" />}
          >
            {countsLoading ? "Counting..." : "Find Counts"}
          </Button>
          <Menu anchorEl={countsMenuAnchorEl} open={Boolean(countsMenuAnchorEl)} onClose={handleCountsMenuClose}>
            <MenuItem
              disableRipple
              onClick={(event) => {
                event.stopPropagation();
              }}
            >
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, width: "100%", justifyContent: "space-between" }}>
                <FormControlLabel
                  control={
                    <Switch
                      size="small"
                      checked={countMode === "accurate"}
                      onChange={(event) => setCountMode(event.target.checked ? "accurate" : "fast")}
                    />
                  }
                  label="Accurate counts"
                />
                <Tooltip
                  title={
                    countMode === "accurate"
                      ? "Accurate counts scan all datasets and apply import filters. Slower but matches import size."
                      : "Fast counts use API totals only. Faster but may include non-importable items."
                  }
                >
                  <HelpOutlineIcon fontSize="small" />
                </Tooltip>
              </Box>
            </MenuItem>
            <Divider />
            <MenuItem
              disabled={countsLoading || missingCountPortalIds.length === 0}
              onClick={() => {
                handleCountsMenuClose();
                if (missingCountPortalIds.length) {
                  handleFindCounts(missingCountPortalIds);
                }
              }}
            >
              {`Find Missing Counts (${missingCountPortalIds.length})`}
            </MenuItem>
            <MenuItem
              disabled={countsLoading || selectedPortalIds.length === 0}
              onClick={() => {
                handleCountsMenuClose();
                if (selectedPortalIds.length) {
                  handleFindCounts(selectedPortalIds);
                }
              }}
            >
              {`Find All Counts (${selectedPortalIds.length})`}
            </MenuItem>
          </Menu>
          <Button
            variant="outlined"
            onClick={handleCreateImports}
            disabled={createLoading || countsLoading || selectedPortalIds.length === 0}
            size="small"
          >
            {createLoading ? "Creating..." : `Add to Imports (${selectedPortalIds.length})`}
          </Button>
          <Button variant="text" onClick={() => setKeywordDialogOpen(true)} size="small">
            Keyword Groups
          </Button>
          {countsLoading && countsProgress && (
            <Box sx={{ minWidth: 200 }}>
              <Typography variant="caption" color="text.secondary">
                Counts: {countsProgress.completed}/{countsProgress.total}
                {countsProgress.failed ? ` (${countsProgress.failed} failed)` : ""}
              </Typography>
              <LinearProgress
                variant="determinate"
                value={Math.min(
                  100,
                  (countsProgress.completed / Math.max(countsProgress.total, 1)) * 100
                )}
              />
            </Box>
          )}
        </Box>

        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center", justifyContent: "flex-end" }}>
          <Tooltip title="Refresh cached results">
            <span>
              <IconButton aria-label="Refresh cached results" onClick={refreshCached} disabled={loading} size="small">
                <RefreshIcon fontSize="small" />
              </IconButton>
            </span>
          </Tooltip>
          <TextField
            label="Filter"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            size="small"
            sx={{ minWidth: 220 }}
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={hideZeroDatasets}
                onChange={(event) => setHideZeroDatasets(event.target.checked)}
              />
            }
            label="Hide zero-dataset portals"
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={hideNoMatches}
                onChange={(event) => setHideNoMatches(event.target.checked)}
              />
            }
            label="Hide no-match portals"
          />
          <Box sx={{ minWidth: 180 }}>
            <Typography variant="body2">Total: {filteredResultsWithCounts.length}</Typography>
            <Typography variant="caption" color="text.secondary">
              Refreshed: {formatLocalTimestamp(lastUpdated)}
            </Typography>
          </Box>
          <Box sx={{ minWidth: 180 }}>
            <Typography variant="body2">
              Selected: {selectedRows.length} · Datasets:{" "}
              {selectedDatasetSummary.unknown > 0
                ? `${selectedDatasetSummary.total}+`
                : selectedDatasetSummary.total}
            </Typography>
          </Box>
        </Box>
      </Box>

      <Box sx={{ height: 700, width: "100%" }}>
        <PortalGrid
          rows={sortedResults}
          columns={columns}
          paginationModel={paginationModel}
          onPaginationModelChange={setPaginationModel}
          rowSelectionModel={selectionModel}
          onRowSelectionModelChange={setSelectionModel}
          columnVisibilityModel={columnVisibilityModel}
          onColumnVisibilityModelChange={setColumnVisibilityModel}
          sortModel={sortModel}
          onSortModelChange={setSortModel}
          loading={loading}
        />
      </Box>

      <ErrorDialog
        open={errorDialogOpen}
        onClose={() => setErrorDialogOpen(false)}
        error={error || "Unexpected error"}
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
            value={JSON.stringify(rawTarget?.raw ?? rawTarget ?? {}, null, 2)}
            extensions={[json()]}
            readOnly
            autoFocus
            basicSetup={{ lineNumbers: true, foldGutter: false }}
            style={{ fontSize: 12 }}
          />
        </DialogContent>
      </Dialog>

      <KeywordGroupsDialog
        open={keywordDialogOpen}
        onClose={() => setKeywordDialogOpen(false)}
        keywordGroups={keywordGroups}
        termInputs={termInputs}
        configLoading={configLoading}
        configSaving={configSaving}
        keywordGroupsUpdatedAt={keywordGroupsUpdatedAt}
        onGroupLabelChange={handleGroupLabelChange}
        onRemoveGroup={handleRemoveGroup}
        onAddGroup={handleAddGroup}
        onTermInputChange={handleTermInputChange}
        onAddTerm={handleAddTerm}
        onRemoveTerm={handleRemoveTerm}
        onSave={handleSaveKeywordGroups}
        onReset={handleResetKeywordGroups}
        onResetDefault={handleResetToDefaultGroups}
      />

      <PortalDetailsDialog
        open={detailDialogOpen}
        onClose={() => setDetailDialogOpen(false)}
        portal={detailTarget ?? null}
        arcgisRoot={arcgisRoot}
      />
    </Box>
  );
};

const PortalGrid = React.memo(
  ({
    rows,
    columns,
    paginationModel,
    onPaginationModelChange,
    rowSelectionModel,
    onRowSelectionModelChange,
    columnVisibilityModel,
    onColumnVisibilityModelChange,
    sortModel,
    onSortModelChange,
    loading,
  }: {
    rows: ArcgisPortalCandidate[];
    columns: GridColDef<ArcgisPortalCandidate>[];
    paginationModel: GridPaginationModel;
    onPaginationModelChange: (model: GridPaginationModel) => void;
    rowSelectionModel: GridRowSelectionModel;
    onRowSelectionModelChange: (model: GridRowSelectionModel) => void;
    columnVisibilityModel: Record<string, boolean>;
    onColumnVisibilityModelChange: (model: Record<string, boolean>) => void;
    sortModel: GridSortModel;
    onSortModelChange: (model: GridSortModel) => void;
    loading: boolean;
  }) => (
    <DataGrid<ArcgisPortalCandidate>
      rows={rows}
      columns={columns}
      getRowId={(row) => row.url}
      paginationModel={paginationModel}
      onPaginationModelChange={onPaginationModelChange}
      rowSelectionModel={rowSelectionModel}
      onRowSelectionModelChange={onRowSelectionModelChange}
      columnVisibilityModel={columnVisibilityModel}
      onColumnVisibilityModelChange={onColumnVisibilityModelChange}
      checkboxSelection
      sortModel={sortModel}
      onSortModelChange={onSortModelChange}
      sortingMode="server"
      pageSizeOptions={[10, 25, 50, 100]}
      loading={loading}
      disableRowSelectionOnClick
    />
  )
);

export default ArcgisPortalDiscovery;
