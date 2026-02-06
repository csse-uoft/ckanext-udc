import React from "react";
import {
  Box,
  Button,
  Chip,
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import InfoOutlined from "@mui/icons-material/InfoOutlined";
import CloseIcon from "@mui/icons-material/Close";
import { ArcgisPortalKeywordGroup } from "../../api/api";
import { formatLocalTimestamp } from "../utils/time";

type KeywordGroupsDialogProps = {
  open: boolean;
  keywordGroups: ArcgisPortalKeywordGroup[];
  termInputs: Record<number, string>;
  configLoading: boolean;
  configSaving: boolean;
  keywordGroupsUpdatedAt: string | null;
  onClose: () => void;
  onGroupLabelChange: (index: number, value: string) => void;
  onRemoveGroup: (index: number) => void;
  onAddGroup: () => void;
  onTermInputChange: (index: number, value: string) => void;
  onAddTerm: (index: number) => void;
  onRemoveTerm: (index: number, term: string) => void;
  onSave: () => void;
  onReset: () => void;
  onResetDefault: () => void;
};

const KeywordGroupsDialog: React.FC<KeywordGroupsDialogProps> = ({
  open,
  keywordGroups,
  termInputs,
  configLoading,
  configSaving,
  keywordGroupsUpdatedAt,
  onClose,
  onGroupLabelChange,
  onRemoveGroup,
  onAddGroup,
  onTermInputChange,
  onAddTerm,
  onRemoveTerm,
  onSave,
  onReset,
  onResetDefault,
}) => {
  const [showHelp, setShowHelp] = React.useState(false);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", pr: 1 }}>
        <span>Keyword Groups</span>
        <Tooltip title="Close">
          <IconButton aria-label="Close" onClick={onClose} size="small">
            <CloseIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </DialogTitle>
      <DialogContent>
        <Box sx={{ mb: 2, display: "flex", alignItems: "center", gap: 1 }}>
          <Typography variant="body2">How it works</Typography>
          <Tooltip title="Show details">
            <IconButton size="small" onClick={() => setShowHelp((prev) => !prev)}>
              <InfoOutlined fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
        {showHelp ? (
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2">
              Keyword groups control which ArcGIS Hub sites are discovered. Each group runs as a separate
              search query to avoid the 10,000-result cap per query.
            </Typography>
            <Typography variant="body2" sx={{ mt: 1 }}>
              Terms are matched against tags, snippet, description, and portal name (case-insensitive).
              Group labels are for organization only and are not used in the search query.
            </Typography>
            <Typography variant="body2" sx={{ mt: 1 }}>
              Save changes to apply them on the next discovery run. Empty or duplicate terms are ignored.
            </Typography>
          </Box>
        ) : null}
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
          {configLoading ? (
            <Typography variant="body2">Loading keyword groups...</Typography>
          ) : (
            keywordGroups.map((group, index) => (
              <KeywordGroupRow
                key={`${group.label}-${index}`}
                group={group}
                index={index}
                termInput={termInputs[index] ?? ""}
                onGroupLabelChange={onGroupLabelChange}
                onRemoveGroup={onRemoveGroup}
                onTermInputChange={onTermInputChange}
                onAddTerm={onAddTerm}
                onRemoveTerm={onRemoveTerm}
              />
            ))
          )}
          <Button variant="outlined" size="small" onClick={onAddGroup} disabled={configLoading}>
            Add keyword group
          </Button>
        </Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mt: 2, flexWrap: "wrap" }}>
          <Button
            variant="outlined"
            color="warning"
            onClick={onReset}
            disabled={configLoading || configSaving}
            size="small"
          >
            Reset to last saved
          </Button>
          <Button
            variant="outlined"
            color="warning"
            onClick={onResetDefault}
            disabled={configLoading || configSaving}
            size="small"
          >
            Load system default
          </Button>
          <Button
            variant="outlined"
            onClick={onSave}
            disabled={configLoading || configSaving}
            size="small"
          >
            {configSaving ? "Saving..." : "Save Keyword Groups"}
          </Button>
          <Typography variant="caption" color="text.secondary">
            Last saved: {formatLocalTimestamp(keywordGroupsUpdatedAt)}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Save changes to use them in the next discovery run.
          </Typography>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

type KeywordGroupRowProps = {
  group: ArcgisPortalKeywordGroup;
  index: number;
  termInput: string;
  onGroupLabelChange: (index: number, value: string) => void;
  onRemoveGroup: (index: number) => void;
  onTermInputChange: (index: number, value: string) => void;
  onAddTerm: (index: number) => void;
  onRemoveTerm: (index: number, term: string) => void;
};

const KeywordGroupRow = React.memo(
  ({
    group,
    index,
    termInput,
    onGroupLabelChange,
    onRemoveGroup,
    onTermInputChange,
    onAddTerm,
    onRemoveTerm,
  }: KeywordGroupRowProps) => (
    <Box
      sx={{
        border: "1px solid",
        borderColor: "divider",
        borderRadius: 1,
        p: 1.5,
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
        <TextField
          label="Group label"
          value={group.label}
          onChange={(e) => onGroupLabelChange(index, e.target.value)}
          size="small"
          sx={{ minWidth: 200 }}
        />
        <Button variant="text" color="error" size="small" onClick={() => onRemoveGroup(index)}>
          Remove group
        </Button>
      </Box>
      <Box sx={{ mt: 1.5 }}>
        <Typography variant="body2" sx={{ mb: 0.5 }}>
          Terms
        </Typography>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
          {(group.terms ?? []).length === 0 ? (
            <Typography variant="caption" color="text.secondary">
              No terms yet.
            </Typography>
          ) : (
            group.terms.map((term) => (
              <Chip
                key={`${term}-${index}`}
                label={term}
                onDelete={() => onRemoveTerm(index, term)}
                size="small"
              />
            ))
          )}
        </Box>
        <Box sx={{ display: "flex", gap: 1, mt: 1, flexWrap: "wrap" }}>
          <TextField
            label="Add terms (comma separated)"
            value={termInput}
            onChange={(e) => onTermInputChange(index, e.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                onAddTerm(index);
              }
            }}
            size="small"
            sx={{ minWidth: 240 }}
          />
          <Button variant="outlined" size="small" onClick={() => onAddTerm(index)}>
            Add terms
          </Button>
        </Box>
      </Box>
    </Box>
  ),
  (prev, next) => prev.group === next.group && prev.termInput === next.termInput
);

export default KeywordGroupsDialog;
