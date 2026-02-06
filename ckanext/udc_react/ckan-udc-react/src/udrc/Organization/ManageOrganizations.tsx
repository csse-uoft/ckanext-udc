import React, { useEffect, useMemo, useState } from "react";
import { DataGrid, GridColDef, GridPaginationModel, GridRowSelectionModel } from "@mui/x-data-grid";
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  IconButton,
  TextField,
  Typography,
} from "@mui/material";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import Tooltip from "@mui/material/Tooltip";
import { useApi } from "../../api/useApi";
import ErrorDialog from "../License/ErrorDialog";
import {
  OrganizationListFilters,
  OrganizationPackageSummary,
  OrganizationSummary,
} from "../../api/api";
import { formatLocalTimestamp } from "../../import/utils/time";

const ManageOrganizations: React.FC = () => {
  const { api, executeApiCall } = useApi();
  const [organizations, setOrganizations] = useState<OrganizationSummary[]>([]);
  const [orgTotal, setOrgTotal] = useState(0);
  const [orgLoading, setOrgLoading] = useState(false);
  const [orgPaginationModel, setOrgPaginationModel] = useState<GridPaginationModel>({
    page: 0,
    pageSize: 25,
  });
  const [orgFilterDraft, setOrgFilterDraft] = useState<OrganizationListFilters>({ q: "", name: "", title: "" });
  const [orgFilters, setOrgFilters] = useState<OrganizationListFilters>({});
  const [selectedOrg, setSelectedOrg] = useState<OrganizationSummary | null>(null);

  const [packages, setPackages] = useState<OrganizationPackageSummary[]>([]);
  const [packageTotal, setPackageTotal] = useState(0);
  const [packageLoading, setPackageLoading] = useState(false);
  const [packagePaginationModel, setPackagePaginationModel] = useState<GridPaginationModel>({
    page: 0,
    pageSize: 25,
  });
  const [packageFilterDraft, setPackageFilterDraft] = useState<OrganizationListFilters>({ q: "", name: "", title: "" });
  const [packageFilters, setPackageFilters] = useState<OrganizationListFilters>({});
  const [packageSelection, setPackageSelection] = useState<GridRowSelectionModel>([]);
  const [selectAllLoading, setSelectAllLoading] = useState(false);

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [errorDialogOpen, setErrorDialogOpen] = useState(false);

  const loadOrganizations = async () => {
    setOrgLoading(true);
    try {
      const result = await executeApiCall(() =>
        api.listOrganizations({
          page: orgPaginationModel.page + 1,
          page_size: orgPaginationModel.pageSize,
          filters: orgFilters,
        })
      );
      setOrganizations(result.results);
      setOrgTotal(result.total);
    } catch (err) {
      setError("Failed to load organizations.");
      setErrorDialogOpen(true);
    } finally {
      setOrgLoading(false);
    }
  };

  const loadPackages = async () => {
    if (!selectedOrg?.id) {
      setPackages([]);
      setPackageTotal(0);
      return;
    }
    setPackageLoading(true);
    try {
      const result = await executeApiCall(() =>
        api.listOrganizationPackages({
          org_id: selectedOrg.id,
          page: packagePaginationModel.page + 1,
          page_size: packagePaginationModel.pageSize,
          filters: packageFilters,
        })
      );
      setPackages(result.results);
      setPackageTotal(result.total);
    } catch (err) {
      setError("Failed to load organization packages.");
      setErrorDialogOpen(true);
    } finally {
      setPackageLoading(false);
    }
  };

  useEffect(() => {
    loadOrganizations();
  }, [orgPaginationModel, orgFilters]);

  useEffect(() => {
    loadPackages();
  }, [selectedOrg, packagePaginationModel, packageFilters]);

  const handleApplyOrgFilters = () => {
    setOrgPaginationModel((prev) => ({ ...prev, page: 0 }));
    setOrgFilters({ ...orgFilterDraft });
  };

  const handleClearOrgFilters = () => {
    setOrgFilterDraft({ q: "", name: "", title: "" });
    setOrgPaginationModel((prev) => ({ ...prev, page: 0 }));
    setOrgFilters({});
  };

  const handleApplyPackageFilters = () => {
    setPackagePaginationModel((prev) => ({ ...prev, page: 0 }));
    setPackageFilters({ ...packageFilterDraft });
  };

  const handleClearPackageFilters = () => {
    setPackageFilterDraft({ q: "", name: "", title: "" });
    setPackagePaginationModel((prev) => ({ ...prev, page: 0 }));
    setPackageFilters({});
  };

  const handleSelectAllPackages = async () => {
    if (!selectedOrg?.id) {
      return;
    }
    setSelectAllLoading(true);
    try {
      const result = await executeApiCall(() =>
        api.listOrganizationPackageIds({ org_id: selectedOrg.id, filters: packageFilters })
      );
      setPackageSelection(result.ids);
    } catch (err) {
      setError("Failed to select all packages.");
      setErrorDialogOpen(true);
    } finally {
      setSelectAllLoading(false);
    }
  };

  const handleDeleteSelected = async () => {
    if (!selectedOrg?.id || packageSelection.length === 0) {
      return;
    }
    setDeleteLoading(true);
    try {
      await executeApiCall(() =>
        api.deleteOrganizationPackages({
          org_id: selectedOrg.id,
          ids: packageSelection.map((value) => String(value)),
        })
      );
      setDeleteDialogOpen(false);
      setPackageSelection([]);
      loadPackages();
    } catch (err) {
      setError("Failed to delete packages.");
      setErrorDialogOpen(true);
    } finally {
      setDeleteLoading(false);
    }
  };

  const orgColumns: GridColDef<OrganizationSummary>[] = useMemo(
    () => [
      { field: "name", headerName: "Name", flex: 1, minWidth: 160 },
      { field: "title", headerName: "Title", flex: 1, minWidth: 200 },
      { field: "state", headerName: "State", width: 120 },
      {
        field: "public",
        headerName: "Public",
        width: 90,
        sortable: false,
        renderCell: (params) => (
          <Tooltip title="Open public organization page">
            <span>
              <IconButton
                size="small"
                aria-label="Open public organization page"
                href={`/organization/${params.row?.name ?? ""}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                <OpenInNewIcon fontSize="small" />
              </IconButton>
            </span>
          </Tooltip>
        ),
      },
    ],
    []
  );

  const packageColumns: GridColDef<OrganizationPackageSummary>[] = useMemo(
    () => [
      { field: "name", headerName: "Name", flex: 1, minWidth: 180 },
      { field: "title", headerName: "Title", flex: 1, minWidth: 220 },
      { field: "state", headerName: "State", width: 120 },
      {
        field: "metadata_modified",
        headerName: "Last Modified",
        minWidth: 180,
        renderCell: (params) => (
          <Typography variant="body2">
            {formatLocalTimestamp(params.row?.metadata_modified ?? null)}
          </Typography>
        ),
      },
      {
        field: "public",
        headerName: "Public",
        width: 90,
        sortable: false,
        renderCell: (params) => (
          <Tooltip title="Open public dataset page">
            <span>
              <IconButton
                size="small"
                aria-label="Open public dataset page"
                href={`/dataset/${params.row?.name ?? ""}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                <OpenInNewIcon fontSize="small" />
              </IconButton>
            </span>
          </Tooltip>
        ),
      },
    ],
    []
  );

  const selectedOrgLabel = selectedOrg?.title || selectedOrg?.name || "Select an organization";

  return (
    <Box sx={{ width: "100%", display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1.6fr" }, gap: 2 }}>
      <Box>
        <Typography variant="h6" sx={{ mb: 1 }}>
          Organizations
        </Typography>
        <Box sx={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 1, mb: 1 }}>
          <TextField
            label="Search"
            value={orgFilterDraft.q}
            onChange={(e) => setOrgFilterDraft((prev) => ({ ...prev, q: e.target.value }))}
            size="small"
          />
          <TextField
            label="Name"
            value={orgFilterDraft.name}
            onChange={(e) => setOrgFilterDraft((prev) => ({ ...prev, name: e.target.value }))}
            size="small"
          />
          <TextField
            label="Title"
            value={orgFilterDraft.title}
            onChange={(e) => setOrgFilterDraft((prev) => ({ ...prev, title: e.target.value }))}
            size="small"
          />
        </Box>
        <Box sx={{ display: "flex", gap: 1, mb: 1 }}>
          <Button variant="contained" size="small" onClick={handleApplyOrgFilters}>
            Apply
          </Button>
          <Button variant="text" size="small" onClick={handleClearOrgFilters}>
            Clear
          </Button>
        </Box>
        <DataGrid
          rows={organizations}
          columns={orgColumns}
          loading={orgLoading}
          disableRowSelectionOnClick
          paginationModel={orgPaginationModel}
          onPaginationModelChange={setOrgPaginationModel}
          pageSizeOptions={[25, 50, 100]}
          paginationMode="server"
          rowCount={orgTotal}
          getRowId={(row) => row.id}
          onRowClick={(params) => {
            setSelectedOrg(params.row);
            setPackagePaginationModel((prev) => ({ ...prev, page: 0 }));
            setPackageSelection([]);
          }}
          sx={{ height: 620 }}
        />
      </Box>

      <Box>
        <Typography variant="h6" sx={{ mb: 1 }}>
          Packages: {selectedOrgLabel}
        </Typography>
        <Box sx={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 1, mb: 1 }}>
          <TextField
            label="Search"
            value={packageFilterDraft.q}
            onChange={(e) => setPackageFilterDraft((prev) => ({ ...prev, q: e.target.value }))}
            size="small"
            disabled={!selectedOrg}
          />
          <TextField
            label="Name"
            value={packageFilterDraft.name}
            onChange={(e) => setPackageFilterDraft((prev) => ({ ...prev, name: e.target.value }))}
            size="small"
            disabled={!selectedOrg}
          />
          <TextField
            label="Title"
            value={packageFilterDraft.title}
            onChange={(e) => setPackageFilterDraft((prev) => ({ ...prev, title: e.target.value }))}
            size="small"
            disabled={!selectedOrg}
          />
        </Box>
        <Box sx={{ display: "flex", gap: 1, mb: 1, flexWrap: "wrap" }}>
          <Button variant="contained" size="small" onClick={handleApplyPackageFilters} disabled={!selectedOrg}>
            Apply
          </Button>
          <Button variant="text" size="small" onClick={handleClearPackageFilters} disabled={!selectedOrg}>
            Clear
          </Button>
          <Button
            variant="outlined"
            size="small"
            onClick={handleSelectAllPackages}
            disabled={!selectedOrg || selectAllLoading}
          >
            {selectAllLoading ? "Selecting..." : "Select All (filtered)"}
          </Button>
          <Button
            variant="outlined"
            color="error"
            size="small"
            disabled={!selectedOrg || packageSelection.length === 0}
            onClick={() => setDeleteDialogOpen(true)}
          >
            Delete Selected ({packageSelection.length})
          </Button>
        </Box>
        <DataGrid
          rows={packages}
          columns={packageColumns}
          loading={packageLoading}
          disableRowSelectionOnClick
          paginationModel={packagePaginationModel}
          onPaginationModelChange={setPackagePaginationModel}
          pageSizeOptions={[25, 50, 100]}
          paginationMode="server"
          rowCount={packageTotal}
          getRowId={(row) => row.id}
          checkboxSelection
          rowSelectionModel={packageSelection}
          onRowSelectionModelChange={setPackageSelection}
          sx={{ height: 620 }}
        />
      </Box>

      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Delete Packages</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Delete {packageSelection.length} package(s) from {selectedOrgLabel}? This will mark them as deleted.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleDeleteSelected} color="error" variant="contained" disabled={deleteLoading}>
            {deleteLoading ? "Deleting..." : "Delete"}
          </Button>
        </DialogActions>
      </Dialog>

      <ErrorDialog
        open={errorDialogOpen}
        onClose={() => setErrorDialogOpen(false)}
        error={error || "Unexpected error"}
      />
    </Box>
  );
};

export default ManageOrganizations;
