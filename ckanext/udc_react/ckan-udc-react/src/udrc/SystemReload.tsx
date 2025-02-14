import React, { useState } from "react";
import {
  Button,
  Select,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  CircularProgress,
  Typography,
} from "@mui/material";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import { useApi } from "../api/useApi";
import { Container } from "@mui/system";


const SystemReload: React.FC = () => {
  const [service, setService] = useState<string>("ckan");
  const [loading, setLoading] = useState<boolean>(false);
  const [open, setOpen] = useState<boolean>(false);
  const { api, executeApiCall } = useApi();

  const handleReload = async () => {
    setLoading(true);
    try {
      await executeApiCall(() => api.reloadSupervisor(service));
      while (true) {
        try {
          await executeApiCall(() => api.getCurrentUser());
          break;
        } catch (error) {
        }
      }

    } catch (error) {
      window.location.reload();
    } finally {
      setLoading(false);
      setOpen(false);
    }
  };

  return (
    <Container>
      <FormControl fullWidth sx={{ marginBottom: 2 }}>
        <InputLabel>Service</InputLabel>
        <Select
          label="Service"
          value={service}
          onChange={(e) => setService(e.target.value)}
        >
          <MenuItem value="ckan">CKAN</MenuItem>
          <MenuItem value="worker">Worker</MenuItem>
          <MenuItem value="all">All</MenuItem>
        </Select>
      </FormControl>

      <Button
        variant="contained"
        color="primary"
        startIcon={<RestartAltIcon />}
        onClick={() => setOpen(true)}
        disabled={loading}
      >
        Reload
      </Button>

      {/* Confirmation Dialog */}
      <Dialog open={open} onClose={() => setOpen(false)}>
        <DialogTitle>Confirm Reload</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to reload <b>{service}</b>?
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)} color="secondary">
            Cancel
          </Button>
          <Button
            onClick={handleReload}
            color="primary"
            variant="contained"
            disabled={loading}
          >
            {loading ? <CircularProgress size={24} /> : "Reload"}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default SystemReload;
