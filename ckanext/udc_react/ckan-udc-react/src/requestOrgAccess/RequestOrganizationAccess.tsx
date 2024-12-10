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
import { useLocation, useParams } from 'react-router-dom';
import { Dialog as ErrorDialog } from './Dialog';


const getAdminLabel = (admin: CKANUser) => {
  const optional = [];
  if (admin.fullname) {
    optional.push("username: " + admin.name);
  }
  if (admin.sysadmin) {
    optional.push('sysadmin');
  } else {
    optional.push('organization admin');
  }
  const optionalText = optional.length > 0 ? ` (${optional.join(', ')})` : '';

  if (admin.fullname) {
    return `${admin.fullname}${optionalText}`;
  } else {
    return `${admin.name}${optionalText}`;
  }
}


const RequestOrganizationAccess: React.FC = () => {
  const [organizations, setOrganizations] = useState<CKANOrganizationAndAdmin[]>([]);
  const [selectedOrg, setSelectedOrg] = useState<CKANOrganizationAndAdmin | null>(null);
  const [selectedAdmins, setSelectedAdmins] = useState<CKANUser[]>([]);
  const [message, setMessage] = useState<string>('');
  const [success, setSuccess] = useState<boolean>(false);
  const [requesting, setRequesting] = useState<boolean>(false);
  const [showError, setShowError] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string>('Request failed, please try again later.');
  const { executeApiCall, api } = useApi();
  const { option } = useParams()
  const showAlert = option === 'redirected';

  const location = useLocation();

  useEffect(() => {
    document.title = 'Request Organization Access - CUDC';

    (async function () {
      const user = await executeApiCall(api.getCurrentUser);
      if (user.id == null) {
        window.location.href = '/user/login?came_from=' + location.pathname;
      } else {
        // Fetch organizations and admins from API
        const data = await executeApiCall(api.getOrganizationsAndAdmins);
        for (const org of data.organizations) {
          // Add sysadmins to each organization
          const adminIds = new Set(org.admins.map(admin => admin.id));

          for (const sysadmin of data.sysadmins) {
            if (!adminIds.has(sysadmin.id)) {
              org.admins.push({ ...sysadmin, sysadmin: true });
              console.log(org.admins)
            }
          }
        }
        setOrganizations(data.organizations);
      }

    })();
  }, []);

  useEffect(() => {
    setSelectedAdmins([]);
  }, [selectedOrg]);

  const handleSubmit = async () => {
    setRequesting(true);
    console.log('Request submitted:', {
      organization: selectedOrg,
      admins: selectedAdmins,
    });

    // Send request to API
    executeApiCall(() => api.requestOrganizationAccess(selectedOrg?.id!, selectedAdmins.map(admin => admin.id), message)).then(() => {
      setSuccess(true);
      setRequesting(false);
    }).catch((error) => {
      if (error instanceof Error) {
        error = error.message;
      }
      console.error('Request failed:', error);
      if (typeof error == 'string') {
        setErrorMessage(error);
        setShowError(true);
        setRequesting(false);
      }

    });

  };

  const handleClose = () => {
    setRequesting(false);
    setSuccess(false);
  }

  const handleCloseError = () => {
    setShowError(false);
  }


  if (organizations.length === 0) {
    return <Container>
      <Typography variant="h5" gutterBottom>
        Loading...
      </Typography>
    </Container>
  }

  return (
    <Container>

      {showAlert && (
        <Alert severity="error" sx={{ mb: 2, mt: 2 }}>
          You do not have access to any organizations. Please request access to an organization to proceed.
          <br />See <Link href="/udc-react/faq/create-catalogue-entry" target="_blank">tutorial</Link> for more information.
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
          getOptionLabel={getAdminLabel}
          value={selectedAdmins}
          onChange={(event, newValue) => setSelectedAdmins(newValue)}
          renderInput={(params) => <TextField {...params} label="Admins of selected organization to notify" variant="outlined" />}
          sx={{ mb: 2 }}
          disabled={!selectedOrg}
        />

        <TextField
          label="Message"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          multiline
          rows={4}
          variant="outlined"
          fullWidth
          sx={{ mb: 2 }}
          helperText="Optional message to send to the admins"
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
        <ErrorDialog open={showError} onClose={handleCloseError} message={errorMessage} />
      </Paper>
    </Container>

  );
};

export default RequestOrganizationAccess;
