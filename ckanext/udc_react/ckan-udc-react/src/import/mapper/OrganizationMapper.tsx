import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Typography,
  Button,
  List,
  ListItem,
  ListItemText,
  Paper,
  Modal,
  IconButton,
  Fade,
  CircularProgress,
  Autocomplete,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tooltip,
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import SearchIcon from '@mui/icons-material/Search';
import DeleteIcon from '@mui/icons-material/Delete';
import CloseIcon from '@mui/icons-material/Close';
import { useApi } from '../../api/useApi';
import { CKANOrganization, RemoteOrganizationSummary } from '../../api/api';

interface Organization {
  id: string;
  name: string;
  description: string;
}

interface OrganizationMapperProps {
  externalBaseApi: string;
  onChange: (mapping: { [k: string]: string }) => void;
  defaultValue?: { [k: string]: string };
}

const OrganizationMapper: React.FC<OrganizationMapperProps> = ({ externalBaseApi, onChange, defaultValue }) => {
  const { api, executeApiCall } = useApi();
  const [organizationsA, setOrganizationsA] = useState<Organization[]>([]);
  const [organizationsB, setOrganizationsB] = useState<Organization[]>([]);
  const [filteredOrganizationsB, setFilteredOrganizationsB] = useState<Organization[]>([]);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [selectedExternalOrg, setSelectedExternalOrg] = useState<Organization | null>(null);
  const [modalOpen, setModalOpen] = useState<boolean>(false);
  const [mapping, setMapping] = useState<{ [k: string]: string }>(defaultValue || {});
  const [loading, setLoading] = useState<boolean>(false);
  const [internalLoaded, setInternalLoaded] = useState(false);
  const [externalLoadedBaseApi, setExternalLoadedBaseApi] = useState<string | null>(null);

  const mapInternalOrg = (org: CKANOrganization): Organization => ({
    id: org.id,
    name: org.title || org.display_name || org.name,
    description: org.description || '',
  });

  const mapExternalOrg = (org: RemoteOrganizationSummary): Organization => ({
    id: org.id,
    name: org.name,
    description: org.description || '',
  });

  const loadOrganizations = async () => {
    if (!modalOpen) {
      return;
    }
    if (!externalBaseApi) {
      return;
    }
    setLoading(true);
    try {
      if (!internalLoaded) {
        const internalOrgs = await executeApiCall(api.getOrganizations);
        const filteredInternal = (internalOrgs || []).filter(
          (org) => org.package_count == null || (org.package_count || 0) > 0
        );
        setOrganizationsA(filteredInternal.map(mapInternalOrg));
        setInternalLoaded(true);
      }
      if (externalLoadedBaseApi !== externalBaseApi) {
        const externalOrgs = await executeApiCall(() => api.getRemoteOrganizations(externalBaseApi));
        const mapped = (externalOrgs || []).map(mapExternalOrg);
        setOrganizationsB(mapped);
        setFilteredOrganizationsB(mapped);
        setExternalLoadedBaseApi(externalBaseApi);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (modalOpen) {
      loadOrganizations();
    }
  }, [modalOpen, externalBaseApi]);

  useEffect(() => {
    setOrganizationsB([]);
    setFilteredOrganizationsB([]);
    setExternalLoadedBaseApi(null);
    setSelectedExternalOrg(null);
  }, [externalBaseApi]);

  useEffect(() => {
    setFilteredOrganizationsB(
      organizationsB.filter((org) =>
        org.name.toLowerCase().includes(searchTerm.toLowerCase())
      )
    );
  }, [searchTerm, organizationsB]);

  const handleExternalOrgSelect = (org: Organization) => {
    setSelectedExternalOrg(org);
  };

  const handleMap = (internalOrg: Organization | null) => {
    if (internalOrg && selectedExternalOrg) {
      setMapping((prevMapping) => {
        const newMapping = { ...prevMapping, [selectedExternalOrg.id]: internalOrg.id };
        onChange(newMapping);
        return newMapping;
      });
    } else if (!internalOrg && selectedExternalOrg) {
      setMapping((prevMapping) => {
        const newMapping = { ...prevMapping };
        delete newMapping[selectedExternalOrg.id];
        onChange(newMapping);
        return newMapping;
      });
    }
    setSelectedExternalOrg(null);
  };

  const handleDeleteMapping = (externalId: string) => {
    setMapping((prevMapping) => {
      const newMapping = { ...prevMapping };
      delete newMapping[externalId];
      onChange(newMapping);
      return newMapping;
    });
  };

  const handleOpenModal = () => {
    setModalOpen(true);
  };

  const handleCloseModal = () => {
    setModalOpen(false);
  };

  return (
    <Box>
      <Button variant='outlined' sx={{ textTransform: 'initial' }} onClick={handleOpenModal} startIcon={<EditIcon />}>
        Organization Mapping
      </Button>
      <Dialog open={modalOpen} onClose={handleCloseModal} fullWidth maxWidth="lg">
        <DialogTitle
          id="alert-dialog-title"
          sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", pr: 1 }}
        >
          <span>Map Organizations</span>
          <Tooltip title="Close">
            <IconButton aria-label="Close" onClick={handleCloseModal} size="small">
              <CloseIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </DialogTitle>
        <DialogContent>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
              <CircularProgress />
            </Box>
          ) : (
            <Grid container spacing={2}>
              {/* External Organization List Panel */}
              <Grid item xs={6}>
                <Paper variant='outlined' sx={{ padding: 2, maxHeight: '70vh' }}>
                  <Typography variant="h6">External Organizations</Typography>
                  <TextField
                    label="Search External Organizations"
                    variant="outlined"
                    fullWidth
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    sx={{ mb: 2, mt: 2 }}
                    InputProps={{
                      startAdornment: (
                        <SearchIcon />
                      ),
                    }}

                  />
                  <List sx={{ maxHeight: 'calc(70vh - 150px)', overflow: 'auto' }}>
                    {filteredOrganizationsB.map((org) => (
                      <ListItem
                        key={org.id}
                        button
                        onClick={() => handleExternalOrgSelect(org)}
                      >
                        <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                          <ListItemText
                            primary={org.name}
                            secondary={mapping[org.id] ? `Mapped to: ${organizationsA.find(internalOrg => internalOrg.id === mapping[org.id])?.name || 'Unknown'}` : ''}
                          />
                          {selectedExternalOrg?.id === org.id && (
                            <Box sx={{ mt: 2 }}>
                              <Autocomplete
                                defaultValue={organizationsA.find(internalOrg => internalOrg.id === mapping[org.id])}
                                options={organizationsA}
                                getOptionLabel={(option) => option?.name || ''}
                                onChange={(_, value) => handleMap(value)}
                                renderInput={(params) => (
                                  <TextField
                                    {...params}
                                    label="Select Internal Organization"
                                    variant="outlined"
                                    fullWidth
                                  />
                                )}
                              />
                            </Box>

                          )}

                        </Box>

                      </ListItem>
                    ))}
                  </List>
                </Paper>
              </Grid>

              {/* Mapping Result Panel */}
              <Grid item xs={6}>
                <Paper variant='outlined' sx={{ padding: 2, maxHeight: '70vh', overflow: 'auto' }}>
                  <Typography variant="h6">Mapped Organizations</Typography>
                  <List>
                    {Object.entries(mapping).map(([externalId, internalId]) => {
                      const externalOrg = organizationsB.find((org) => org.id === externalId);
                      const internalOrg = organizationsA.find((org) => org.id === internalId);

                      return (
                        <ListItem key={externalId}>
                          <ListItemText
                            primary={externalOrg ? externalOrg.name : `External Org ID: ${externalId}`}
                            secondary={internalOrg ? `Mapped to: ${internalOrg.name}` : `Internal Org ID: ${internalId}`}
                          />
                          <Tooltip title="Remove mapping">
                            <IconButton edge="end" onClick={() => handleDeleteMapping(externalId)}>
                              <DeleteIcon />
                            </IconButton>
                          </Tooltip>
                        </ListItem>
                      );
                    })}
                  </List>
                </Paper>
              </Grid>
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseModal} variant="contained" color="primary">Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default OrganizationMapper;
