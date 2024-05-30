import * as React from 'react';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import { Fade } from '@mui/material';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function CustomTabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <Fade in={value === index}>
      <div
        role="tabpanel"
        hidden={value !== index}
        {...other}
      >
        {value === index && (
          <Box sx={{ p: 3 }}>
            {children}
          </Box>
        )}
      </div>
    </Fade>
  );
}

export interface IDynamicTab { key: string, label: string, panel: JSX.Element }

export interface DynamicTabsProps {
  tabs: IDynamicTab[];
}


export default function DynamicTabs(props: DynamicTabsProps) {
  const [value, setValue] = React.useState(0);

  const handleChange = (event: React.SyntheticEvent, newValue: number) => {
    setValue(newValue);
  };

  return (
    <Box sx={{ width: '100%' }}>
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>

        <Tabs value={value} onChange={handleChange} aria-label="import tabs">
          {props.tabs.map((tab, index) =>
            <Tab label={tab.label} key={tab.key + index} sx={{
              textTransform: "none",
              fontWeight: value === index ? 600 : null,
              background: value === index ? "#e1f0ff" : null
            }} />)}
        </Tabs>
      </Box>
      {props.tabs.map((tab, index) =>
        <CustomTabPanel value={value} index={index} key={tab.key + index}>
          {tab.panel}
        </CustomTabPanel>
      )}

    </Box>
  );
}