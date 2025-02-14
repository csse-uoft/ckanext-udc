import React, { useEffect, useState, useMemo } from "react";
import { DataGrid, GridColDef, GridPaginationModel, GridFilterModel } from "@mui/x-data-grid";
import { useApi } from "../../api/useApi";
import { Box, Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle } from "@mui/material";
import LicenseDialog, { SLicense } from "./LicenseDialog";
import ErrorDialog from "./ErrorDialog";
import LicenseActions from "./LicenseActions";
import { License } from "../../api/api";

const ManageLicenses: React.FC = () => {
  const { api, executeApiCall } = useApi();
  const [licenses, setLicenses] = useState<License[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedLicense, setSelectedLicense] = useState<License | null>(null);
  const [dialogOpen, setDialogOpen] = useState<boolean>(false);
  const [errorDialogOpen, setErrorDialogOpen] = useState<boolean>(false);
  const [licenseDialogMode, setLicenseDialogMode] = useState<"edit" | "create">("edit");
  const [deleteDialogOpen, setDeleteDialogOpen] = useState<boolean>(false);
  const [licenseToDelete, setLicenseToDelete] = useState<string | null>(null);

  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({
    page: 0,
    pageSize: 25,
  });

  const [filterModel, setFilterModel] = useState<GridFilterModel>({ items: [] });

  useEffect(() => {
    const fetchLicenses = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await executeApiCall(() => api.getLicenses());
        setLicenses(result);
      } catch (err) {
        setError("Failed to load licenses.");
        setErrorDialogOpen(true);
      } finally {
        setLoading(false);
      }
    };

    fetchLicenses();
  }, []);

  const handleEditClick = (license: License) => {
    setSelectedLicense(license);
    setLicenseDialogMode("edit");
    setDialogOpen(true);
  };

  const handleDeleteClick = (id: string) => {
    setLicenseToDelete(id);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (licenseToDelete) {
      try {
        await executeApiCall(() => api.deleteLicense({ id: licenseToDelete }));
        setLicenses((prev) => prev.filter((l) => l.id !== licenseToDelete));
      } catch (err) {
        if (typeof err === "string") {
          setError(err);
        } else {
          setError("Failed to delete license.");
        }
        setErrorDialogOpen(true);
      } finally {
        setDeleteDialogOpen(false);
        setLicenseToDelete(null);
      }
    }
  };

  const handleDialogClose = () => {
    setDialogOpen(false);
    setSelectedLicense(null);
  };

  const handleErrorDialogClose = () => {
    setErrorDialogOpen(false);
    setTimeout(() => setError(null), 500);
  };

  const handleSave = async (updatedLicense: SLicense) => {
    try {
      if (licenseDialogMode === "create") {
        await executeApiCall(() => api.createLicense(updatedLicense));
      } else {
        await executeApiCall(() => api.updateLicense(updatedLicense));
      }
      await executeApiCall(() => api.getLicenses()).then(setLicenses);
      handleDialogClose();
    } catch (err) {
      setError("Failed to update license.");
      setErrorDialogOpen(true);
    }
  };

  const columns: GridColDef[] = useMemo(
    () => [
      { field: "id", headerName: "License ID", width: 200, sortable: true },
      { field: "title", headerName: "Title", width: 300, sortable: true },
      {
        field: "url",
        headerName: "URL",
        width: 250,
        sortable: true,
        renderCell: (params) => <a href={params.row.url} target="_blank" rel="noopener noreferrer">{params.value}</a>,
      },
      {
        field: "user",
        headerName: "Created By",
        width: 200,
        sortable: true,
        renderCell: (params) =>
          params.row.user.fullname ? `${params.row.user.fullname} (${params.row.user.name})` : params.row.user.name,
      },
      {
        field: "actions",
        headerName: "Actions",
        width: 200,
        sortable: false,
        renderCell: (params) => (
          <LicenseActions
            licenseId={params.row.id}
            onEdit={() => handleEditClick(params.row)}
            onDelete={() => handleDeleteClick(params.row.id)}
          />
        ),
      },
    ],
    []
  );

  return (
    <Box sx={{ height: 650, width: "100%" }}>
      <Button variant="outlined" onClick={() => {
        setLicenseDialogMode("create");
        setDialogOpen(true);
      }}>Create License</Button>
      <DataGrid
        rows={licenses}
        columns={columns}
        loading={loading}
        disableRowSelectionOnClick
        paginationModel={paginationModel}
        onPaginationModelChange={setPaginationModel}
        filterModel={filterModel}
        onFilterModelChange={setFilterModel}
        pageSizeOptions={[25, 50, 100]}
        initialState={{
          sorting: {
            sortModel: [{ field: 'id', sort: 'asc' }],
          },
        }}
      />

      <LicenseDialog open={dialogOpen} license={selectedLicense} mode={licenseDialogMode} onClose={handleDialogClose} onSave={handleSave} />
      <ErrorDialog open={errorDialogOpen} error={error} onClose={handleErrorDialogClose} />

      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <DialogContentText>Are you sure you want to delete this license?</DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleDeleteConfirm} color="primary">Delete</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ManageLicenses;
