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
  IconButton,
  LinearProgress,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import InfoOutlined from "@mui/icons-material/InfoOutlined";
import LockResetOutlined from "@mui/icons-material/LockResetOutlined";
import DeleteOutline from "@mui/icons-material/DeleteOutline";
import { useApi } from "../../api/useApi";
import ErrorDialog from "../License/ErrorDialog";
import { UserListFilters, UserSummary } from "../../api/api";
import { Markdown } from "../../tutorial/Markdown";

const ManageUsers: React.FC = () => {
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

  const [resetDialogOpen, setResetDialogOpen] = useState(false);
  const [resetPassword, setResetPassword] = useState("");
  const [resetTarget, setResetTarget] = useState<UserSummary | null>(null);

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<UserSummary | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteDoneCount, setDeleteDoneCount] = useState(0);
  const [deleteTotalCount, setDeleteTotalCount] = useState(0);
  const [selectionModel, setSelectionModel] = useState<GridRowSelectionModel>([]);
  const [selectAllLoading, setSelectAllLoading] = useState(false);
  const [selectAllScannedCount, setSelectAllScannedCount] = useState(0);
  const [selectAllTotalCount, setSelectAllTotalCount] = useState(0);
  const [selectAllFetchedCount, setSelectAllFetchedCount] = useState(0);
  const selectAllCancelRef = useRef(false);
  const [aboutDialogOpen, setAboutDialogOpen] = useState(false);
  const [aboutTarget, setAboutTarget] = useState<UserSummary | null>(null);
  const isSelectableUser = (user: UserSummary) => !user.sysadmin;

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await executeApiCall(() =>
        api.listUsers({
          page: paginationModel.page + 1,
          page_size: paginationModel.pageSize,
          filters,
        })
      );
      setUsers(result.results);
      setTotal(result.total);
    } catch (err) {
      setError("Failed to load users.");
      setErrorDialogOpen(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [paginationModel, filters]);

  const fetchAllUserIds = async () => {
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
        api.listUsers({
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
      const { ids } = await fetchAllUserIds();
      setSelectionModel(ids);
    } catch (err) {
      setError("Failed to select all users across all pages.");
      setErrorDialogOpen(true);
      setSelectionModel(sanitizedModel);
    } finally {
      setSelectAllLoading(false);
      selectAllCancelRef.current = false;
    }
  };

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

  const handleResetPassword = async () => {
    if (!resetTarget || !resetPassword) {
      return;
    }
    try {
      await executeApiCall(() =>
        api.resetUserPassword({ id: resetTarget.id, new_password: resetPassword })
      );
      setResetDialogOpen(false);
      setResetPassword("");
      setResetTarget(null);
    } catch (err) {
      setError("Failed to reset password.");
      setErrorDialogOpen(true);
    }
  };

  const handleDeleteUser = async () => {
    const selectedIds =
      deleteTarget?.id ? [deleteTarget.id] : selectionModel.map((id) => String(id));
    if (!selectedIds.length) {
      return;
    }
    setDeleteLoading(true);
    setDeleteDoneCount(0);
    setDeleteTotalCount(selectedIds.length);
    try {
      let done = 0;
      const failedIds: string[] = [];
      for (const id of selectedIds) {
        try {
          await executeApiCall(() => api.deleteUser({ id }));
        } catch (err) {
          failedIds.push(id);
        }
        done += 1;
        setDeleteDoneCount(done);
      }
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
      setSelectionModel(failedIds);
      fetchUsers();
      if (failedIds.length) {
        setError(
          `Delete finished with partial failures. Succeeded: ${selectedIds.length - failedIds.length}, failed: ${failedIds.length}.`
        );
        setErrorDialogOpen(true);
      }
    } catch (err) {
      setError("Failed to delete user.");
      setErrorDialogOpen(true);
    } finally {
      setDeleteLoading(false);
    }
  };

  const columns: GridColDef[] = useMemo(
    () => [
      {
        field: "name",
        headerName: "Username",
        flex: 1,
        minWidth: 180,
        renderCell: (params) => (
          <a href={`/user/${params.value}`} target="_blank" rel="noopener noreferrer">
            {params.value}
          </a>
        ),
      },
      { field: "fullname", headerName: "Full Name", flex: 1, minWidth: 200 },
      { field: "email", headerName: "Email", flex: 1, minWidth: 240 },
      { field: "state", headerName: "State", width: 120 },
      {
        field: "sysadmin",
        headerName: "Sysadmin",
        width: 120,
        valueFormatter: (params: { value?: boolean }) => (params.value ? "Yes" : "No"),
      },
      {
        field: "actions",
        headerName: "Actions",
        width: 140,
        sortable: false,
        display: "flex",
        renderCell: (params) => (
          <Box sx={{ display: "flex", gap: 1, alignItems: "center", justifyContent: "center", width: "100%" }}>
            <Tooltip title="View About">
              <IconButton
                size="small"
                onClick={() => {
                  setAboutTarget(params.row);
                  setAboutDialogOpen(true);
                }}
              >
                <InfoOutlined fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title="Reset Password">
              <IconButton
                size="small"
                onClick={() => {
                  setResetTarget(params.row);
                  setResetPassword("");
                  setResetDialogOpen(true);
                }}
              >
                <LockResetOutlined fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title="Delete User">
              <IconButton
                size="small"
                color="error"
                onClick={() => {
                  setDeleteTarget(params.row);
                  setDeleteDialogOpen(true);
                }}
              >
                <DeleteOutline fontSize="small" />
              </IconButton>
            </Tooltip>
          </Box>
        ),
      },
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
          onClick={() => {
            setDeleteTarget(null);
            setDeleteDialogOpen(true);
          }}
        >
          Delete Selected ({selectionModel.length})
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
        disableRowSelectionOnClick
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

      <Dialog open={resetDialogOpen} onClose={() => setResetDialogOpen(false)}>
        <DialogTitle>Reset Password</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Set a new password for {resetTarget?.name}.
          </DialogContentText>
          <TextField
            margin="dense"
            label="New Password"
            type="password"
            fullWidth
            value={resetPassword}
            onChange={(e) => setResetPassword(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResetDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleResetPassword} variant="contained">
            Reset
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={deleteDialogOpen}
        onClose={() => {
          if (!deleteLoading) {
            setDeleteDialogOpen(false);
          }
        }}
      >
        <DialogTitle>{deleteTarget ? "Delete User" : "Delete Users"}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {deleteTarget
              ? `Delete user ${deleteTarget.name}? This will mark the user as deleted.`
              : `Delete ${selectionModel.length} selected user(s)? This will mark them as deleted.`}
          </DialogContentText>
          {deleteLoading && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" sx={{ mb: 0.5 }}>
                Deleting... {deleteDoneCount} / {deleteTotalCount}
              </Typography>
              <LinearProgress
                variant={deleteTotalCount ? "determinate" : "indeterminate"}
                value={deleteTotalCount ? (deleteDoneCount / deleteTotalCount) * 100 : undefined}
              />
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)} disabled={deleteLoading}>
            Cancel
          </Button>
          <Button onClick={handleDeleteUser} color="error" variant="contained" disabled={deleteLoading}>
            {deleteLoading ? "Deleting..." : "Delete"}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={aboutDialogOpen}
        onClose={() => setAboutDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>About {aboutTarget?.name}</DialogTitle>
        <DialogContent dividers sx={{ maxHeight: 500 }}>
          {aboutTarget?.about ? (
            <Markdown>{aboutTarget.about}</Markdown>
          ) : (
            <DialogContentText>No about text provided.</DialogContentText>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAboutDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      <ErrorDialog open={errorDialogOpen} error={error} onClose={() => setErrorDialogOpen(false)} />
    </Box>
  );
};

export default ManageUsers;
