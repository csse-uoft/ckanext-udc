import * as React from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  Avatar,
  Typography,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Alert,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import HourglassEmptyIcon from "@mui/icons-material/HourglassEmpty";
import ErrorIcon from "@mui/icons-material/Error";
import CloseIcon from "@mui/icons-material/Close";
import { Pending, PendingActions, PendingOutlined, PendingRounded } from "@mui/icons-material";

// Task Data Type
export interface Task {
  id: string;
  title: string;
  summary: string;
  status: "pending" | "success" | "failed" | "processing";
}

// Status Icons
const getStatusIcon = (status: Task["status"]) => {
  switch (status) {
    case "success":
      return <CheckCircleIcon color="success" />;
    case "failed":
      return <ErrorIcon color="error" />;
    case "pending":
    default:
      return <Pending color="info" />;
  }
};

// Task Dialog Component
interface TaskDialogProps {
  open: boolean;
  tasks: Task[];
  onClose: () => void;
  onClearTasks: () => void;
}

export const TaskDialog: React.FC<TaskDialogProps> = ({ open, tasks, onClose, onClearTasks }) => {
  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="lg">
      <DialogTitle>
        Task Status
        <IconButton
          aria-label="close"
          onClick={onClose}
          sx={{ position: "absolute", right: 8, top: 8 }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        
        <Alert severity="warning">Do not navigate away from this page until all tasks are completed. You are safe to close this dialog.</Alert>

        {tasks.length === 0 ? (
          <Typography variant="body1" align="center" sx={{ mt: 2 }}>
            No tasks available.
          </Typography>
        ) : (
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Index</TableCell>
                <TableCell>ID</TableCell>
                <TableCell>Title</TableCell>
                <TableCell>Summary</TableCell>
                <TableCell>Status</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {tasks.map((task, index) => (
                <TableRow key={task.id}>
                  <TableCell>{index + 1}</TableCell>
                  <TableCell>{task.id}</TableCell>
                  <TableCell>{task.title}</TableCell>
                  <TableCell>
                    <Typography noWrap title={task.summary}>
                      {task.summary.split(" ").slice(0, 5).join(" ")} {task.summary.split(" ").length > 5 ? "..." : ""}
                    </Typography>
                  </TableCell>
                  <TableCell>{getStatusIcon(task.status)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClearTasks} variant="contained">
          Clear
        </Button>
        <Button onClick={onClose} variant="contained">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default TaskDialog;
