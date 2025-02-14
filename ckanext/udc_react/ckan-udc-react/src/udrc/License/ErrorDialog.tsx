import React from "react";
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, Typography } from "@mui/material";

interface ErrorDialogProps {
  open: boolean;
  error: string | null;
  onClose: () => void;
}

const ErrorDialog: React.FC<ErrorDialogProps> = ({ open, error, onClose }) => {
  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>Error</DialogTitle>
      <DialogContent>
        <Typography>{error}</Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};

export default ErrorDialog;
