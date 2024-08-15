import React from 'react';
import PackageSearchTable from './PackageSearchTable'; // Adjust the path as necessary
import { Paper } from '@mui/material';
import { Box } from '@mui/system';

const ManagerSummary: React.FC = () => {
  return (
    <Box sx={{ p: 2, m: 1 }}>
      <h1>Manage Catalogue Summary</h1>
      <PackageSearchTable />
    </Box>
  );
};

export default ManagerSummary;
