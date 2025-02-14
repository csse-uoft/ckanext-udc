import React, { useState, useEffect } from "react";
import {
  Card,
  CardContent,
  Typography,
  Tab,
  Tabs,
  Box,
  Button,
  CircularProgress,
  Paper,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import { useApi } from "../api/useApi";


const CodeBlock: React.FC<{ data: string }> = ({ data }) => (
  <Paper sx={{ p: 2, backgroundColor: "#f4f4f4", overflowX: "auto", }}>
    <Typography sx={{ fontFamily: "monospace", whiteSpace: "pre", fontSize: "0.9rem" }}>
      {data}
    </Typography>
  </Paper>
);


interface SystemStats {
  cpu_usage: string;
  memory_usage: string;
  disk_usage: string;
}

const CKANSystemStats: React.FC = () => {
  const [tab, setTab] = useState(0);
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const { api, executeApiCall } = useApi();


  const fetchStats = async () => {
    setLoading(true);
    try {
      const data = await executeApiCall(() => api.getSystemStats());
      setStats(data);
    } catch (error) {
      console.error("Error fetching system stats:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  return (
    <Card>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">UDRC System Stats</Typography>
          <Button
            variant="contained"
            color="primary"
            startIcon={loading ? <CircularProgress size={20} /> : <RefreshIcon />}
            onClick={fetchStats}
            disabled={loading}
          >
            Refresh
          </Button>
        </Box>
        <Tabs value={tab} onChange={(_, newValue) => setTab(newValue)} variant="fullWidth">
          <Tab label="CPU Usage" />
          <Tab label="Memory Usage" />
          <Tab label="Disk Usage" />
        </Tabs>
        <Box sx={{ p: 2 }}>
          {loading ? (
            <Typography>Loading...</Typography>
          ) : stats ? (
            <>
              {tab === 0 && <CodeBlock data={stats.cpu_usage} />}
              {tab === 1 && <CodeBlock data={stats.memory_usage} />}
              {tab === 2 && <CodeBlock data={stats.disk_usage} />}
            </>
          ) : (
            <Typography color="error">Failed to load system stats.</Typography>
          )}
        </Box>
      </CardContent>
    </Card>
  );
};

export default CKANSystemStats;
