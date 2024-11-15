import { Card, CardContent, Typography, Box, LinearProgress, Select, MenuItem, FormControl, InputLabel, Button } from '@mui/material';
import Grid from '@mui/material/Unstable_Grid2'; // Grid version 2
import { useEffect, useState } from 'react';
import { io, Socket } from "socket.io-client";
import { useApi } from '../../api/useApi';
import { ImportLog, ImportProgress, RunningJob, ImportPanelProps, FinishedPackage } from './types';
import { LogsPanel } from './LogsPanel'; // Import LogsPanel
import { FinishedPackagesTable } from './FinishedPackagesTable';

export function RealtimeImportPanel(props: ImportPanelProps) {
  const { api, executeApiCall } = useApi();
  const [importLogs, setImportLogs] = useState<ImportLog[]>([]); // Only store the new incoming logs
  const [importProgress, setImportProgress] = useState<ImportProgress>({ current: 0, total: 1 });
  const [finishedPackages, setFinishedPackages] = useState<FinishedPackage[]>([]); // List of finished packages
  const [runningJobs, setRunningJobs] = useState<RunningJob[]>([]);
  const [selectedJob, setSelectedJob] = useState<string>("");
  const [socket, setSocket] = useState<Socket>();
  const [autoScroll, setAutoScroll] = useState(true); // Auto-scroll state

  useEffect(() => {
    let socket: Socket;
    (async function () {
      const token = await executeApiCall(() => api.getWsToken());
      socket = io(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/admin-dashboard`, {
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
        setImportLogs([log]); // Send the new log directly to LogsPanel
      });

      // Listen for finished packages
      socket.on('finish_one', (data: FinishedPackage) => {
        if (data.data.duplications)
          console.log("Finished package:", data);
        setFinishedPackages((prevPackages) => [...prevPackages, data]);
      });

      socket.on('job_started', (job: RunningJob) => {
        console.log("job_started", job);
        if (job.import_config_id === props.uuid) {
          setRunningJobs((prevJobs) => {
            if (prevJobs.find((j) => j.id === job.id)) {
              return prevJobs;
            } else {
              return [...prevJobs, job];
            }
          });
          if (!selectedJob) {
            // Reset
            setSelectedJob(job.id);
            setImportLogs([]);
            setFinishedPackages([]);
            setImportProgress({ current: 0, total: 1 });
          }
        }
      });

      socket.on('job_stopped', (jobId) => {
        console.log("job_stopped", jobId);
        if (jobId === selectedJob) {
          // Keep the logs and finished packages if the job is stopped
          setSelectedJob("");
        }
        setRunningJobs((prevJobs) => prevJobs.filter((job) => job.id !== jobId));
      });

    })();

    return () => socket && socket.close() && setSocket(undefined);
  }, [props.uuid]);

  const handleJobSelection = (event: any) => {
    const jobId = event.target.value as string;
    setSelectedJob(jobId);
  };

  useEffect(() => {
    socket?.emit('subscribe', selectedJob);
    socket?.emit('get_job_status', selectedJob);
    socket?.once('job_status', (status: { progress: ImportProgress, logs: ImportLog[], finished: FinishedPackage[] }) => {
      console.log(status)
      if (status.progress)
        setImportProgress(status.progress);
      setImportLogs(status.logs);
      setFinishedPackages(status.finished);
    });
  }, [selectedJob]);

  const handleJobStop = () => {
    socket?.emit('stop_job', selectedJob);
  };

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

      {socket && selectedJob && (
        <>
          <Grid xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6">Progress</Typography>
                <Typography variant="body2" color="textSecondary">
                  {importLogs.length > 0 ? importLogs[0].message : ''}
                </Typography>
                <Box width="100%" mr={1}>
                  <LinearProgress variant="determinate" value={(importProgress.current / importProgress.total) * 100} />
                </Box>
                <Box sx={{ pt: 2 }}>
                  <Typography variant="body2" color="textSecondary">
                    {`${Math.round((importProgress.current / importProgress.total) * 100)}% ${importProgress.current}/${importProgress.total}`}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* <Grid xs={12}>
            <LogsPanel importLogs={importLogs} autoScroll={autoScroll} />
          </Grid> */}

          <Grid xs={12}>
            <FinishedPackagesTable finishedPackages={finishedPackages} />
          </Grid>

          <Button variant="outlined" color="error" onClick={handleJobStop} disabled={!selectedJob} sx={{mt: 1}}>Stop</Button>
        </>
      )}
    </Grid>
  );
}
