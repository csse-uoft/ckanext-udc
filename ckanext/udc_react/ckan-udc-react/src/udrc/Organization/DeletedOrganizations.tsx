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
  TextField,
} from "@mui/material";
import { useApi } from "../../api/useApi";
import ErrorDialog from "../License/ErrorDialog";
import { OrganizationListFilters, OrganizationSummary } from "../../api/api";

const DeletedOrganizations: React.FC = () => {
  const { api, executeApiCall } = useApi();
  const [organizations, setOrganizations] = useState<OrganizationSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorDialogOpen, setErrorDialogOpen] = useState(false);

  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({
    page: 0,
    pageSize: 25,
  });
  const [filterDraft, setFilterDraft] = useState<OrganizationListFilters>({
    q: "",
    name: "",
    title: "",
  });
  const [filters, setFilters] = useState<OrganizationListFilters>({});

  const [selectionModel, setSelectionModel] = useState<GridRowSelectionModel>([]);
  const [purgeDialogOpen, setPurgeDialogOpen] = useState(false);
  const [purgeLoading, setPurgeLoading] = useState(false);

  const fetchDeletedOrganizations = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await executeApiCall(() =>
        api.listDeletedOrganizations({
          page: paginationModel.page + 1,
          page_size: paginationModel.pageSize,
          filters,
        })
      );
      setOrganizations(result.results);
      setTotal(result.total);
    } catch (err) {
      setError("Failed to load deleted organizations.");
      setErrorDialogOpen(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDeletedOrganizations();
  }, [paginationModel, filters]);

  const handleApplyFilters = () => {
    setPaginationModel((prev) => ({ ...prev, page: 0 }));
    setFilters({ ...filterDraft });
  };

  const handleClearFilters = () => {
    setFilterDraft({ q: "", name: "", title: "" });
    setPaginationModel((prev) => ({ ...prev, page: 0 }));
    setFilters({});
  };

  const handleSelectAllOnPage = () => {
    const ids = new Set(selectionModel.map((id) => String(id)));
    organizations.forEach((org) => ids.add(org.id));
    setSelectionModel(Array.from(ids));
  };

  const handlePurge = async () => {
    if (!selectionModel.length) {
      return;
    }
    setPurgeLoading(true);
    try {
      const selectedIds = selectionModel.map((id) => String(id));
      const result = await executeApiCall(() =>
        api.purgeDeletedOrganizations({ ids: selectedIds })
      );
      setPurgeDialogOpen(false);
      if (result.errors?.length) {
        setError(
          `Purge completed with partial failures. Purged: ${result.purged}, failed: ${result.errors.length}.`
        );
        setErrorDialogOpen(true);
      }
      const failedIds = (result.errors || []).map((item) => item.id);
      setSelectionModel(failedIds);
      fetchDeletedOrganizations();
    } catch (err) {
      setError("Failed to purge deleted organizations.");
      setErrorDialogOpen(true);
    } finally {
      setPurgeLoading(false);
    }
  };

  const columns: GridColDef<OrganizationSummary>[] = useMemo(
    () => [
      { field: "name", headerName: "Name", flex: 1, minWidth: 200 },
      { field: "title", headerName: "Title", flex: 1, minWidth: 260 },
      { field: "state", headerName: "State", width: 120 },
      { field: "created", headerName: "Created", minWidth: 200, flex: 1 },
    ],
    []
  );

  return (
    <Box sx={{ width: "100%" }}>
      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 1, mb: 1 }}>
        <TextField
          label="Search"
          value={filterDraft.q}
          onChange={(e) => setFilterDraft((prev) => ({ ...prev, q: e.target.value }))}
          size="small"
        />
        <TextField
          label="Name"
          value={filterDraft.name}
          onChange={(e) => setFilterDraft((prev) => ({ ...prev, name: e.target.value }))}
          size="small"
        />
        <TextField
          label="Title"
          value={filterDraft.title}
          onChange={(e) => setFilterDraft((prev) => ({ ...prev, title: e.target.value }))}
          size="small"
        />
      </Box>
      <Box sx={{ display: "flex", gap: 1, mb: 1 }}>
        <Button variant="contained" size="small" onClick={handleApplyFilters}>
          Apply
        </Button>
        <Button variant="text" size="small" onClick={handleClearFilters}>
          Clear
        </Button>
        <Button variant="text" size="small" onClick={handleSelectAllOnPage}>
          Select All on Page
        </Button>
        <Button
          variant="outlined"
          color="error"
          size="small"
          disabled={!selectionModel.length}
          onClick={() => setPurgeDialogOpen(true)}
        >
          Purge Selected ({selectionModel.length})
        </Button>
      </Box>

      <DataGrid
        rows={organizations}
        columns={columns}
        loading={loading}
        checkboxSelection
        keepNonExistentRowsSelected
        paginationModel={paginationModel}
        onPaginationModelChange={(model) =>
          setPaginationModel({ page: model.page, pageSize: model.pageSize })
        }
        pageSizeOptions={[25, 50, 100, 1000, 5000]}
        paginationMode="server"
        rowCount={total}
        getRowId={(row) => row.id}
        rowSelectionModel={selectionModel}
        onRowSelectionModelChange={(model) => setSelectionModel(model)}
        sx={{ height: 700 }}
      />

      <Dialog open={purgeDialogOpen} onClose={() => setPurgeDialogOpen(false)}>
        <DialogTitle>Purge Organizations</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Purge {selectionModel.length} deleted organization(s)? This cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPurgeDialogOpen(false)}>Cancel</Button>
          <Button onClick={handlePurge} color="error" variant="contained" disabled={purgeLoading}>
            {purgeLoading ? "Purging..." : "Purge"}
          </Button>
        </DialogActions>
      </Dialog>

      <ErrorDialog open={errorDialogOpen} onClose={() => setErrorDialogOpen(false)} error={error || "Unexpected error"} />
    </Box>
  );
};

export default DeletedOrganizations;

