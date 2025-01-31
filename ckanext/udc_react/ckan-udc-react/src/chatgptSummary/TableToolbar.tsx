import * as React from "react";
import {
  GridToolbarContainer,
  GridToolbarExport,
  GridToolbarColumnsButton,
  GridToolbarFilterButton,
} from "@mui/x-data-grid";
import { Button, Checkbox, FormControlLabel, Icon, ToggleButton } from "@mui/material";
import { Edit, ShowChart } from "@mui/icons-material";

interface UseCustomToolbarProps {
  onGenerateSummary: () => void;
  onClickShowTasks: () => void;
}

export const useCustomToolbar = ({ onGenerateSummary, onClickShowTasks }: UseCustomToolbarProps) => {

  return React.useMemo(() => {
    return function CustomToolbar() {
      return (
        <GridToolbarContainer>
          <GridToolbarColumnsButton />
          <GridToolbarFilterButton />
          <GridToolbarExport />
          <Button
            variant="text"
            color="primary"
            onClick={onGenerateSummary}
            startIcon={<Edit />}
          >
            Generate Summary
          </Button>
          <Button
            variant="text"
            color="primary"
            onClick={onClickShowTasks}
            startIcon={<ShowChart />}
          >
            Show tasks
          </Button>
        </GridToolbarContainer>
      );
    };
  }, [onGenerateSummary]);
};
