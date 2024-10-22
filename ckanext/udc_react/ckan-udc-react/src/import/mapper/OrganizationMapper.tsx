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
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import SearchIcon from '@mui/icons-material/Search';
import DeleteIcon from '@mui/icons-material/Delete';

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
  const [organizationsA, setOrganizationsA] = useState<Organization[]>([]);
  const [organizationsB, setOrganizationsB] = useState<Organization[]>([]);
  const [filteredOrganizationsB, setFilteredOrganizationsB] = useState<Organization[]>([]);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [selectedExternalOrg, setSelectedExternalOrg] = useState<Organization | null>(null);
  const [modalOpen, setModalOpen] = useState<boolean>(false);
  const [mapping, setMapping] = useState<{ [k: string]: string }>(defaultValue || {});
  const [loading, setLoading] = useState<boolean>(false);

  const fetchOrganizations = async (baseApi: string) => {
    try {
      setLoading(true);
      const response = await fetch(`${baseApi}/3/action/organization_list?all_fields=true&limit=10000`);
      const data = await response.json();
      return data.result
        .filter((org: any) => org.package_count > 0)
        .reduce((acc: { [key: string]: Organization }, org: any) => {
          acc[org.id] = {
            id: org.id,
            name: org.title,
            description: org.description,
          };
          return acc;
        }, {});
    } catch (error) {
      console.error('Error fetching organizations:', error);
      return {};
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      const fetchedOrganizationsA = await fetchOrganizations('/api');
      setOrganizationsA(Object.values(fetchedOrganizationsA));
      const fetchedOrganizationsB = await fetchOrganizations(externalBaseApi);
      setOrganizationsB(Object.values(fetchedOrganizationsB));
      setFilteredOrganizationsB(Object.values(fetchedOrganizationsB));
      setLoading(false);
    };
    fetchData();
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
        <DialogTitle id="alert-dialog-title">
          {"Map Organizations"}
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
                          <IconButton edge="end" onClick={() => handleDeleteMapping(externalId)}>
                            <DeleteIcon />
                          </IconButton>
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
