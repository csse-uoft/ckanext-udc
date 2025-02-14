import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  CircularProgress,
} from "@mui/material";

export interface SLicense {
  id: string;
  title: string;
  url: string;
}
interface LicenseDialogProps {
  open: boolean;
  license: SLicense | null;
  mode: "create" | "edit";
  onClose: () => void;
  onSave: (license: SLicense) => Promise<void>;
}

const LicenseDialog: React.FC<LicenseDialogProps> = ({
  open,
  license,
  mode,
  onClose,
  onSave,
}) => {
  const [localLicense, setLocalLicense] = useState<SLicense | null>(license);
  const [saving, setSaving] = useState<boolean>(false);

  useEffect(() => {
    if (mode === "edit") {
      setLocalLicense(license);
    } else {
      setLocalLicense({ 
        id: "",
        title: "",
        url: "",
       });
    }
  }, [license, mode]);

  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>{mode === "edit" ? "Edit License" : "Create License"}</DialogTitle>
      <DialogContent>
        <TextField
          margin="dense"
          label="ID"
          fullWidth
          variant="outlined"
          value={localLicense?.id || ""}
          onChange={(e) =>
            setLocalLicense((prev) => (prev ? { ...prev, id: e.target.value } : null))
          }
          disabled={mode === "edit"}
        />
        <TextField
          autoFocus
          margin="dense"
          label="Title"
          fullWidth
          variant="outlined"
          value={localLicense?.title || ""}
          onChange={(e) =>
            setLocalLicense((prev) => (prev ? { ...prev, title: e.target.value } : null))
          }
        />
        <TextField
          margin="dense"
          label="URL"
          fullWidth
          variant="outlined"
          value={localLicense?.url || ""}
          onChange={(e) =>
            setLocalLicense((prev) => (prev ? { ...prev, url: e.target.value } : null))
          }
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          variant="contained"
          color="primary"
          disabled={saving}
          onClick={async () => {
            if (localLicense) {
              setSaving(true);
              await onSave(localLicense);
              setSaving(false);
              setLocalLicense({ 
                id: "",
                title: "",
                url: "",
               });
            }
          }}
        >
          {saving ? <CircularProgress size={24} /> : "Save"} 
          
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default LicenseDialog;
