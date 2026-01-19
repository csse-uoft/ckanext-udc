import React, { useEffect, useMemo, useState } from "react";
import { DataGrid, GridColDef, GridPaginationModel, GridRowSelectionModel } from "@mui/x-data-grid";
import { Box, Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, TextField } from "@mui/material";
import { useApi } from "../../api/useApi";
import ErrorDialog from "../License/ErrorDialog";
import { UserListFilters, UserSummary } from "../../api/api";

const DeletedUsers: React.FC = () => {
  const { api, executeApiCall } = useApi();
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorDialogOpen, setErrorDialogOpen] = useState(false);

  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({
    page: 0,
    pageSize: 25,
  });

  const [filterDraft, setFilterDraft] = useState<UserListFilters>({
    q: "",
    name: "",
    fullname: "",
    email: "",
    about: "",
  });
  const [filters, setFilters] = useState<UserListFilters>({});

  const [selectionModel, setSelectionModel] = useState<GridRowSelectionModel>([]);
  const [purgeDialogOpen, setPurgeDialogOpen] = useState(false);

  const fetchDeletedUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await executeApiCall(() =>
        api.listDeletedUsers({
          page: paginationModel.page + 1,
          page_size: paginationModel.pageSize,
          filters,
        })
      );
      setUsers(result.results);
      setTotal(result.total);
    } catch (err) {
      setError("Failed to load deleted users.");
      setErrorDialogOpen(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDeletedUsers();
  }, [paginationModel, filters]);

  const handleApplyFilters = () => {
    setPaginationModel((prev) => ({ ...prev, page: 0 }));
    setFilters({ ...filterDraft });
  };

  const handleClearFilters = () => {
    setFilterDraft({ q: "", name: "", fullname: "", email: "", about: "" });
    setPaginationModel((prev) => ({ ...prev, page: 0 }));
    setFilters({});
  };

  const handleSelectAllPage = () => {
    setSelectionModel(users.map((user) => user.id));
  };

  const handlePurge = async () => {
    if (!selectionModel.length) {
      return;
    }
    try {
      await executeApiCall(() => api.purgeDeletedUsers({ ids: selectionModel as string[] }));
      setSelectionModel([]);
      setPurgeDialogOpen(false);
      fetchDeletedUsers();
    } catch (err) {
      setError("Failed to purge users.");
      setErrorDialogOpen(true);
    }
  };

  const columns: GridColDef[] = useMemo(
    () => [
      { field: "name", headerName: "Username", flex: 1, minWidth: 180 },
      { field: "fullname", headerName: "Full Name", flex: 1, minWidth: 200 },
      { field: "email", headerName: "Email", flex: 1, minWidth: 240 },
      { field: "created", headerName: "Created", flex: 1, minWidth: 180 },
    ],
    []
  );

  return (
    <Box sx={{ height: 700, width: "100%" }}>
      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(5, minmax(0, 1fr))", gap: 2, mb: 2 }}>
        <TextField
          label="Search"
          value={filterDraft.q}
          onChange={(e) => setFilterDraft((prev) => ({ ...prev, q: e.target.value }))}
          placeholder="Name, full name, or email"
        />
        <TextField
          label="Username"
          value={filterDraft.name}
          onChange={(e) => setFilterDraft((prev) => ({ ...prev, name: e.target.value }))}
        />
        <TextField
          label="Full Name"
          value={filterDraft.fullname}
          onChange={(e) => setFilterDraft((prev) => ({ ...prev, fullname: e.target.value }))}
        />
        <TextField
          label="Email"
          value={filterDraft.email}
          onChange={(e) => setFilterDraft((prev) => ({ ...prev, email: e.target.value }))}
        />
        <TextField
          label="About"
          value={filterDraft.about}
          onChange={(e) => setFilterDraft((prev) => ({ ...prev, about: e.target.value }))}
        />
      </Box>
      <Box sx={{ display: "flex", gap: 1, mb: 2 }}>
        <Button variant="outlined" onClick={handleApplyFilters}>
          Apply Filters
        </Button>
        <Button variant="text" onClick={handleClearFilters}>
          Clear
        </Button>
        <Button variant="text" onClick={handleSelectAllPage}>
          Select All on Page
        </Button>
        <Button
          variant="outlined"
          color="error"
          disabled={!selectionModel.length}
          onClick={() => setPurgeDialogOpen(true)}
        >
          Purge Selected
        </Button>
      </Box>

      <DataGrid
        rows={users}
        columns={columns}
        loading={loading}
        checkboxSelection
        paginationModel={paginationModel}
        onPaginationModelChange={setPaginationModel}
        pageSizeOptions={[25, 50, 100]}
        paginationMode="server"
        rowCount={total}
        rowSelectionModel={selectionModel}
        onRowSelectionModelChange={setSelectionModel}
      />

      <Dialog open={purgeDialogOpen} onClose={() => setPurgeDialogOpen(false)}>
        <DialogTitle>Purge Users</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Purge {selectionModel.length} selected user(s)? This cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPurgeDialogOpen(false)}>Cancel</Button>
          <Button onClick={handlePurge} color="error" variant="contained">
            Purge
          </Button>
        </DialogActions>
      </Dialog>

      <ErrorDialog open={errorDialogOpen} error={error} onClose={() => setErrorDialogOpen(false)} />
    </Box>
  );
};

export default DeletedUsers;
