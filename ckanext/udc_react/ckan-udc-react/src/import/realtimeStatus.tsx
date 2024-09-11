import { Container, Card, CardContent, Typography, Box, LinearProgress, Select, MenuItem, FormControl, InputLabel, Button, Toolbar } from '@mui/material';
import Grid from '@mui/material/Unstable_Grid2'; // Grid version 2
import CodeMirror from "@uiw/react-codemirror";
import { useEffect, useState, useRef } from 'react';
import DeleteIcon from '@mui/icons-material/Delete';
import { useApi } from '../api/useApi';
import { io, Socket } from "socket.io-client";
import { List, AutoSizer } from 'react-virtualized';
import DynamicTabs, { IDynamicTab } from './tabs';
import { IImportConfig } from './import';
import 'react-virtualized/styles.css'; // Import styles for react-virtualized
import { DefaultEventsMap } from '@socket.io/component-emitter';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';

export interface ImportPanelProps {
  uuid: string;
  defaultName?: string;
  defaultCode?: string;
  onUpdate: (option?: string) => void;
}

interface ImportLog {
  timestamp: string;
  message: string;
  level: string;
}

interface ImportProgress {
  current: number;
  total: number;
}

interface RunningJob {
  id: string;
  import_config_id: string;
  run_at: string;
  run_by: string;
  is_running: boolean;
}


function RealtimeImportPanel(props: ImportPanelProps) {
  const { api, executeApiCall } = useApi();
  const [importLogs, setImportLogs] = useState<ImportLog[]>([]);
  const [importProgress, setImportProgress] = useState<ImportProgress>({ current: 0, total: 1 });
  const [runningJobs, setRunningJobs] = useState<RunningJob[]>([]);
  const [selectedJob, setSelectedJob] = useState<string>("");
  const [socket, setSocket] = useState<Socket>();
  const listRef = useRef<List>(null);
  const logQueueRef = useRef<ImportLog[]>([]); // Queue for incoming logs
  const [isFlushing, setIsFlushing] = useState(false); // To manage flushing state

  useEffect(() => {
    let socket: Socket<DefaultEventsMap, DefaultEventsMap>;
    (async function () {

      // Get Ws token first
      const token = await executeApiCall(() => api.GetWsToken());

      socket = io(`${location.protocol === 'https' ? 'wss' : 'ws'}://${location.host}/admin-dashboard`, {
        reconnectionDelayMax: 10000,
        withCredentials: true,
        transports: ["websocket"],
        auth: {
          token
        }
      });
      setSocket(socket);


      // Fetch running jobs for the import config
      socket.emit('get_running_jobs', props.uuid);

      // Listen for running jobs
      socket.on('running_jobs', (jobs: { [key: string]: RunningJob }) => {
        setRunningJobs(Object.values(jobs));
      });

      // Listen for progress updates
      socket.on('progress_update', (progress: ImportProgress) => {
        setImportProgress(progress);
      });

      // Listen for logs
      socket.on('log_message', (log: ImportLog) => {
        // setImportLogs((prevLogs) => [...prevLogs, log])
        logQueueRef.current.push(log); // Add log to the queue

        if (logQueueRef.current.length === 1) {
          // Start the flushing process if it's not already running
          flushLogQueue();
        }
        // console.log(autoScroll)
      });


    })()


    return () => socket && socket.close();


  }, [props.uuid]);


  const flushLogQueue = () => {
    if (logQueueRef.current.length > 0) {
      setImportLogs((prevLogs) => {
        const list = listRef.current;
        const newLogs = [...prevLogs, ...logQueueRef.current];
        logQueueRef.current = []; // Clear the queue
        console.log(list)
        // Calculate if the user is currently scrolled to the bottom
        const isAtBottom = list
          ? list.scrollHeight - list.scrollTop === list.clientHeight
          : false;

        if (list && isAtBottom) {
          setTimeout(() => list.scrollToRow(newLogs.length - 1), 0); // Scroll to the bottom
        }

        return newLogs;
      });

      // Schedule next flush
      setTimeout(() => {
        if (logQueueRef.current.length > 0) {
          flushLogQueue(); // Continue flushing if more logs are in the queue
        }
      }, 300);
    }
  };

  const handleJobSelection = (event: any) => {
    const jobId = event.target.value as string;
    setSelectedJob(jobId);
  };

  useEffect(() => {
    if (selectedJob) {
      socket?.emit('subscribe', selectedJob);
    }

    return () => {
      if (selectedJob) {
        socket?.emit('unsubscribe', selectedJob);
      }
    };
  }, [selectedJob]);

  // Render each log item
  const renderLogRow = ({ index, key, style }: any) => {
    const log = importLogs[index];
    return (
      <div key={key} style={style}>
        <Typography variant="body2" color="textSecondary">
          {log.level}: {log.message}
        </Typography>
      </div>
    );
  };

  const handleJobStop = () => {
    socket?.emit('stop_job', selectedJob);
    socket?.emit('get_running_jobs', props.uuid);
  }

  return (
    <Grid container spacing={2}>
      <Grid xs={12}>
        <Card>
          <CardContent>
            <Typography variant="h6">Select Running Job</Typography>

            <FormControl fullWidth sx={{ mt: 2 }}>
              <InputLabel id="job-select-label">Job</InputLabel>
              <Select
                label="Job"
                labelId="job-select-label"
                onChange={handleJobSelection}
                value={selectedJob}
              >
                {runningJobs.map((job) => (
                  <MenuItem key={job.id} value={job.id}>
                    {`Job ID: ${job.id}, At: ${new Date(job.run_at).toLocaleString()}`}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </CardContent>
        </Card>
      </Grid>
      {socket && selectedJob &&
        <>
          <Grid xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6">Progress</Typography>
                <Box width="100%" mr={1}>
                  <LinearProgress
                    variant="determinate"
                    value={(importProgress.current / importProgress.total) * 100}
                  />
                </Box>
                <Box sx={{ pt: 2 }}>
                  <Typography variant="body2" color="textSecondary">{`${Math.round(
                    (importProgress.current / importProgress.total) * 100,
                  )}% ${importProgress.current}/${importProgress.total}`}</Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
          <Grid xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6">Logs</Typography>
                <Box height={300} border={1} borderColor="grey.300">
                  
                  <AutoSizer>
                    {({ height, width }) => (
                      <List
                        ref={listRef}
                        width={width}
                        height={height}
                        rowCount={importLogs.length}
                        rowHeight={(idx) => importLogs[idx] ? importLogs[idx].message.split('\n').length * 20 : 20}
                        rowRenderer={renderLogRow}
                      />
                    )}
                  </AutoSizer>
                </Box>
              </CardContent>
            </Card>
          </Grid>
          <Button variant="outlined" color="error" onClick={handleJobStop}>Stop</Button>
        </>
      }

    </Grid>
  );
}

export function RealtimeImportStatus() {
  const { api, executeApiCall } = useApi();

  const [tabs, setTabs] = useState<IDynamicTab[]>([]);

  const load = async (option?: string) => {
    const importConfigs: IImportConfig = await executeApiCall(api.getImportConfigs);
    const newTabs = [];
    for (const [uuid, { code, name }] of Object.entries(importConfigs)) {
      newTabs.push({
        key: uuid,
        label: name,
        panel: <RealtimeImportPanel uuid={uuid} defaultCode={code} defaultName={name} onUpdate={requestRefresh} />
      });
    }
    setTabs(newTabs);
  };

  const requestRefresh = () => {
    load();
  };

  useEffect(() => {
    load();
  }, []);

  if (tabs.length === 0) return "Loading...";

  return (
    <Container>
      <Typography variant='h5' paddingBottom={2}>Realtime Import Status</Typography>
      <DynamicTabs tabs={tabs} />
    </Container>
  );
}
