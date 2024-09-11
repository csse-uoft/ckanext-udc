import React, { useEffect, useState } from 'react';
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, IconButton, Popover, Typography, Tooltip, TablePagination, MenuItem, Select, FormControl, List, ListItem, SelectChangeEvent } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import DeleteIcon from '@mui/icons-material/Delete';
import InfoIcon from '@mui/icons-material/Info';
import VisibilityIcon from '@mui/icons-material/Visibility';
import { FinishedPackage } from './types'; // Updated interface import
import { Link } from 'react-router-dom';

interface FinishedPackagesTableProps {
  finishedPackages: FinishedPackage[];
}

export const FinishedPackagesTable: React.FC<FinishedPackagesTableProps> = ({ finishedPackages }) => {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [logs, setLogs] = useState<string | null>(null);

  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(5);
  const [typeFilter, setTypeFilter] = useState<string>('');

  const handleLogClick = (event: React.MouseEvent<HTMLElement>, logs: string) => {
    setAnchorEl(event.currentTarget);
    setLogs(logs);
  };

  const handlePopoverClose = () => {
    setAnchorEl(null);
    setTimeout(() => setLogs(null), 200); // Delay clearing logs to allow the popover to close
  };

  const open = Boolean(anchorEl);

  const getTypeIcon = (type: FinishedPackage['type']) => {
    switch (type) {
      case 'created':
        return <CheckCircleIcon color="success" />;
      case 'updated':
        return <InfoIcon color="primary" />;
      case 'deleted':
        return <DeleteIcon color="error" />;
      case 'errored':
        return <ErrorIcon color="error" />;
      default:
        return <span />;
    }
  };

  const handleChangeTypeFilter = (event: SelectChangeEvent<string>) => {
    setTypeFilter(event.target.value as string);
    setPage(0);
  };

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const filteredPackages = finishedPackages.filter(pkg => typeFilter === '' || pkg.type === typeFilter);
  const paginatedPackages = filteredPackages.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);

  const duplications = finishedPackages.filter(pkg => pkg.data.duplications && pkg.data.duplications.length > 0); // Filter out packages with duplications

  return (
    <>
      <FormControl fullWidth sx={{ mt: 2, mb: 2 }}>
        <Select
          value={typeFilter}
          onChange={handleChangeTypeFilter}
          displayEmpty
          inputProps={{ 'aria-label': 'Filter by Type' }}
        >
          <MenuItem value="">All</MenuItem>
          <MenuItem value="created">Created</MenuItem>
          <MenuItem value="updated">Updated</MenuItem>
          <MenuItem value="deleted">Deleted</MenuItem>
          <MenuItem value="errored">Errored</MenuItem>
        </Select>
      </FormControl>

      {/* Main Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Type</TableCell>
              <TableCell>Name</TableCell>
              <TableCell>Logs</TableCell>
              <TableCell>Duplications</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {paginatedPackages.map((pkg) => (
              <TableRow key={pkg.data.id}>
                <TableCell>
                  <Tooltip title={pkg.type}>
                    {getTypeIcon(pkg.type)}
                  </Tooltip>
                </TableCell>
                <TableCell>
                  <Link to={`/catalogue/${pkg.data.name}`} target="_blank">
                    {pkg.data.title}
                  </Link>
                </TableCell>
                <TableCell>
                  {pkg.data.logs ? (
                    <Tooltip title="View Logs">
                      <IconButton onClick={(e) => handleLogClick(e, pkg.data.logs!)}>
                        <VisibilityIcon />
                      </IconButton>
                    </Tooltip>
                  ) : (
                    ''
                  )}
                </TableCell>

                <TableCell>
                  {pkg.data.duplications && pkg.data.duplications.length > 0 ? (
                    <List sx={{ paddingTop: 0, paddingBottom: 0 }}>
                      {pkg.data.duplications.map((dup) => (
                        <ListItem key={dup.id} sx={{ padding: 0 }}>
                          <Link to={`/catalogue/${dup.name}`} target="_blank">
                            {dup.title} ({dup.reason})
                          </Link>
                        </ListItem>
                      ))}
                    </List>
                  ) : (
                    ''
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <TablePagination
        component="div"
        count={filteredPackages.length}
        page={page}
        onPageChange={handleChangePage}
        rowsPerPage={rowsPerPage}
        onRowsPerPageChange={handleChangeRowsPerPage}
        rowsPerPageOptions={[5, 10, 25]}
      />

      {/* Duplications Table */}
      {duplications.length > 0 && (
        <>
          <Typography variant="h6" sx={{ mt: 4 }}>Duplications</Typography>
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Imported Package</TableCell>
                  <TableCell>Duplicated Package</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {duplications.map((pkg) =>
                  <TableRow key={pkg.data.id}>
                    <TableCell>
                      <Link to={`/catalogue/${pkg.data.name}`} target="_blank">
                        {pkg.data.title}
                      </Link>
                    </TableCell>

                    <TableCell>
                      {pkg.data.duplications && pkg.data.duplications.length > 0 ? (
                        <List sx={{ paddingTop: 0, paddingBottom: 0 }}>
                          {pkg.data.duplications.map((dup) => (
                            <ListItem key={dup.id} sx={{ padding: 0 }}>
                              <Link to={`/catalogue/${dup.name}`} target="_blank">
                                {dup.title} ({dup.reason})
                              </Link>
                            </ListItem>
                          ))}
                        </List>
                      ) : (
                        ''
                      )}
                    </TableCell>

                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </>
      )}

      <Popover
        open={open}
        anchorEl={anchorEl}
        onClose={handlePopoverClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'center',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'center',
        }}
      >
        <Typography sx={{
          p: 2, whiteSpace: 'pre-line', fontFamily: 'monospace', fontSize: 14,
          color: '#ec3309', backgroundColor: '#F8D8D7', lineHeight: 1.4
        }}>
          {logs ? logs : 'No logs available'}
        </Typography>
      </Popover>
    </>
  );
};
