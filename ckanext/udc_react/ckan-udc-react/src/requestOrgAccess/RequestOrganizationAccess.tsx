import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Typography,
  TextField,
  Snackbar,
  Alert,
  Autocomplete,
  Paper,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Link
} from '@mui/material';
import { useApi } from '../api/useApi';
import { Container } from '@mui/system';
import { CKANOrganizationAndAdmin, CKANUser } from '../api/api';
import { useParams } from 'react-router-dom';


const RequestOrganizationAccess: React.FC = () => {
  const [organizations, setOrganizations] = useState<CKANOrganizationAndAdmin[]>([]);
  const [selectedOrg, setSelectedOrg] = useState<CKANOrganizationAndAdmin | null>(null);
  const [selectedAdmins, setSelectedAdmins] = useState<CKANUser[]>([]);
  const [success, setSuccess] = useState<boolean>(false);
  const [requesting, setRequesting] = useState<boolean>(false);
  const { executeApiCall, api } = useApi();
  const { option } = useParams()
  const showAlert = option === 'redirected';

  useEffect(() => {
    document.title = 'Request Organization Access - CUDC';

    // Fetch organizations and admins from API
    executeApiCall(api.getOrganizationsAndAdmins).then((data: CKANOrganizationAndAdmin[]) => {
      setOrganizations(data);
    });

  }, []);

  useEffect(() => {
    setSelectedAdmins([]);
  }, [selectedOrg]);

  const handleSubmit = () => {
    setRequesting(true);
    console.log('Request submitted:', {
      organization: selectedOrg,
      admins: selectedAdmins,
    });
    setRequesting(false);
    setSuccess(true);
  };

  const handleClose = () => {
    setRequesting(false);
    setSuccess(false);
  }

  return (
    <Container>

      {showAlert && (
        <Alert severity="error" sx={{ mb: 2, mt: 2 }}>
          You do not have access to any organizations. Please request access to an organization to proceed.
          <br/>See <Link href="/udc-react/faq/create-catalogue-entry" target="_blank">tutorial</Link> for more information.
        </Alert>
      )}

      <Paper variant='outlined' sx={{ p: 3, mt: 3, mb: 3 }}>
        <Typography variant="h5" gutterBottom>
          Search for Organizations and Request to Join
        </Typography>

        <Alert severity="info" sx={{ mb: 4, mt: 2 }}>
          You can request to join an organization by choosing the organization and selecting the admins to notify.
        </Alert>

        <Autocomplete
          options={organizations}
          getOptionLabel={(option) => option.name}
          value={selectedOrg}
          onChange={(event, newValue) => setSelectedOrg(newValue)}
          renderInput={(params) => <TextField {...params} label="Organization" variant="outlined" />}
          sx={{ mb: 2 }}
          loading={organizations.length === 0}
        />

        <Autocomplete
          multiple
          options={selectedOrg?.admins || []}
          getOptionLabel={(option) => option.fullname ? `${option.fullname} (${option.name})` : option.name}
          value={selectedAdmins}
          onChange={(event, newValue) => setSelectedAdmins(newValue)}
          renderInput={(params) => <TextField {...params} label="Admins of selected organization to notify" variant="outlined" />}
          sx={{ mb: 2 }}
          disabled={!selectedOrg}
        />

        <Button
          variant="outlined"
          color="primary"
          onClick={handleSubmit}
          disabled={!selectedOrg || selectedAdmins.length === 0 || requesting}
        >
          Request
        </Button>

        <Dialog
          open={success}
          onClose={handleClose}
        >
          <DialogTitle>Success</DialogTitle>
          <DialogContent>
            <DialogContentText>
              Request submitted successfully!
            </DialogContentText>
          </DialogContent>
          <DialogActions>
            <Button onClick={handleClose} color="primary" autoFocus>
              OK
            </Button>
          </DialogActions>
        </Dialog>
      </Paper>
    </Container>

  );
};

export default RequestOrganizationAccess;