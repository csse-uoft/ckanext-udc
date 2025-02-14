import React from "react";
import { IconButton, Link } from "@mui/material";
import { Edit as EditIcon, Delete as DeleteIcon, Search as SearchIcon } from "@mui/icons-material";

interface LicenseActionsProps {
  licenseId: string;
  onEdit: () => void;
  onDelete: () => void;
}

const LicenseActions: React.FC<LicenseActionsProps> = ({ licenseId, onEdit, onDelete }) => {
  return (
    <>
      <IconButton size="small" onClick={onEdit}>
        <EditIcon />
      </IconButton>
      <IconButton size="small" color="error" onClick={onDelete}>
        <DeleteIcon />
      </IconButton>
      <IconButton size="small" href={`/catalogue/?license_id=${licenseId}`} target="_blank">
        <SearchIcon />
      </IconButton>
    </>
  );
};

export default LicenseActions;
