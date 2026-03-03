import React, { useEffect, useMemo, useRef, useState } from "react";
import { DataGrid, GridColDef, GridPaginationModel, GridRowSelectionModel } from "@mui/x-data-grid";
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  LinearProgress,
  TextField,
  Typography,
} from "@mui/material";
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
  const [purgeLoading, setPurgeLoading] = useState(false);
  const [purgeDoneCount, setPurgeDoneCount] = useState(0);
  const [purgeTotalCount, setPurgeTotalCount] = useState(0);
  const [selectAllLoading, setSelectAllLoading] = useState(false);
  const [selectAllScannedCount, setSelectAllScannedCount] = useState(0);
  const [selectAllTotalCount, setSelectAllTotalCount] = useState(0);
  const [selectAllFetchedCount, setSelectAllFetchedCount] = useState(0);
  const selectAllCancelRef = useRef(false);
  const isSelectableUser = (user: UserSummary) => !user.sysadmin;

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
    const ids = new Set(selectionModel.map((id) => String(id)));
    users.filter(isSelectableUser).forEach((user) => ids.add(user.id));
    setSelectionModel(Array.from(ids));
  };

  const fetchAllDeletedUserIds = async () => {
    const ids: string[] = [];
    let page = 1;
    const pageSize = 500;
    let totalCount = 0;
    let fetchedCount = 0;

    do {
      if (selectAllCancelRef.current) {
        return { ids, cancelled: true };
      }
      const result = await executeApiCall(() =>
        api.listDeletedUsers({
          page,
          page_size: pageSize,
          filters,
        })
      );
      if (page === 1) {
        totalCount = result.total;
        setSelectAllTotalCount(result.total);
      }
      fetchedCount += result.results.length;
      setSelectAllScannedCount(fetchedCount);
      ids.push(...result.results.filter(isSelectableUser).map((user) => user.id));
      setSelectAllFetchedCount(ids.length);
      if (!result.results.length) {
        break;
      }
      if (selectAllCancelRef.current) {
        return { ids, cancelled: true };
      }
      page += 1;
    } while (fetchedCount < totalCount);

    return { ids, cancelled: false };
  };

  const handleSelectionChange = async (model: GridRowSelectionModel) => {
    const nonSelectablePageIds = new Set(
      users.filter((user) => !isSelectableUser(user)).map((user) => user.id)
    );
    const sanitizedModel = model.filter((id) => !nonSelectablePageIds.has(String(id)));
    const selectableOnPage = users.filter(isSelectableUser).length;

    if (
      !users.length ||
      !total ||
      total <= users.length ||
      selectableOnPage === 0 ||
      sanitizedModel.length !== selectableOnPage
    ) {
      setSelectionModel(sanitizedModel);
      return;
    }

    const currentPageIds = new Set(users.filter(isSelectableUser).map((user) => user.id));
    let selectedCurrentPageCount = 0;
    for (const id of sanitizedModel) {
      if (currentPageIds.has(String(id))) {
        selectedCurrentPageCount += 1;
      }
    }
    const isHeaderSelectAllOnPage = selectedCurrentPageCount === selectableOnPage;
    if (!isHeaderSelectAllOnPage) {
      setSelectionModel(sanitizedModel);
      return;
    }

    try {
      setSelectAllLoading(true);
      setSelectAllScannedCount(0);
      setSelectAllTotalCount(0);
      setSelectAllFetchedCount(0);
      selectAllCancelRef.current = false;
      const { ids } = await fetchAllDeletedUserIds();
      setSelectionModel(ids);
    } catch (err) {
      setError("Failed to select all deleted users across all pages.");
      setErrorDialogOpen(true);
      setSelectionModel(sanitizedModel);
    } finally {
      setSelectAllLoading(false);
      selectAllCancelRef.current = false;
    }
  };

  const handlePurge = async () => {
    if (!selectionModel.length) {
      return;
    }
    const selectedIds = selectionModel.map((id) => String(id));
    setPurgeLoading(true);
    setPurgeDoneCount(0);
    setPurgeTotalCount(selectedIds.length);
    try {
      let done = 0;
      const failedIds: string[] = [];
      for (const id of selectedIds) {
        try {
          await executeApiCall(() => api.purgeDeletedUsers({ ids: [id] }));
        } catch (err) {
          failedIds.push(id);
        }
        done += 1;
        setPurgeDoneCount(done);
      }
      setSelectionModel(failedIds);
      setPurgeDialogOpen(false);
      fetchDeletedUsers();
      if (failedIds.length) {
        setError(
          `Purge finished with partial failures. Succeeded: ${selectedIds.length - failedIds.length}, failed: ${failedIds.length}.`
        );
        setErrorDialogOpen(true);
      }
    } catch (err) {
      setError("Failed to purge users.");
      setErrorDialogOpen(true);
    } finally {
      setPurgeLoading(false);
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
        {selectAllLoading && (
          <Button
            variant="text"
            color="warning"
            onClick={() => {
              selectAllCancelRef.current = true;
            }}
          >
            Cancel Select All ({selectAllFetchedCount})
          </Button>
        )}
        <Button
          variant="outlined"
          color="error"
          disabled={!selectionModel.length}
          onClick={() => setPurgeDialogOpen(true)}
        >
          Purge Selected
        </Button>
      </Box>
      {selectAllLoading && (
        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" sx={{ mb: 0.5 }}>
            Selecting users... scanned {selectAllScannedCount}
            {selectAllTotalCount ? ` / ${selectAllTotalCount}` : ""}, selected{" "}
            {selectAllFetchedCount} (excluding sysadmin)
          </Typography>
          <LinearProgress
            variant={selectAllTotalCount ? "determinate" : "indeterminate"}
            value={selectAllTotalCount ? (selectAllScannedCount / selectAllTotalCount) * 100 : undefined}
          />
        </Box>
      )}

      <DataGrid
        rows={users}
        columns={columns}
        loading={loading || selectAllLoading}
        checkboxSelection
        isRowSelectable={(params) => isSelectableUser(params.row)}
        keepNonExistentRowsSelected
        paginationModel={paginationModel}
        onPaginationModelChange={(model) =>
          setPaginationModel({ page: model.page, pageSize: model.pageSize })
        }
        pageSizeOptions={[25, 50, 100, 1000, 5000]}
        paginationMode="server"
        rowCount={total}
        rowSelectionModel={selectionModel}
        onRowSelectionModelChange={(model) => {
          void handleSelectionChange(model);
        }}
      />

      <Dialog
        open={purgeDialogOpen}
        onClose={() => {
          if (!purgeLoading) {
            setPurgeDialogOpen(false);
          }
        }}
      >
        <DialogTitle>Purge Users</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Purge {selectionModel.length} selected user(s)? This cannot be undone.
          </DialogContentText>
          {purgeLoading && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" sx={{ mb: 0.5 }}>
                Purging... {purgeDoneCount} / {purgeTotalCount}
              </Typography>
              <LinearProgress
                variant={purgeTotalCount ? "determinate" : "indeterminate"}
                value={purgeTotalCount ? (purgeDoneCount / purgeTotalCount) * 100 : undefined}
              />
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPurgeDialogOpen(false)} disabled={purgeLoading}>
            Cancel
          </Button>
          <Button onClick={handlePurge} color="error" variant="contained" disabled={purgeLoading}>
            {purgeLoading ? "Purging..." : "Purge"}
          </Button>
        </DialogActions>
      </Dialog>

      <ErrorDialog open={errorDialogOpen} error={error} onClose={() => setErrorDialogOpen(false)} />
    </Box>
  );
};

export default DeletedUsers;
