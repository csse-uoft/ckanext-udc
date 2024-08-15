// PackageSearchTable.tsx
import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { DataGrid, GridColDef, GridPaginationModel, GridSortModel, GridFilterModel, getGridStringOperators } from '@mui/x-data-grid';
import { useApi } from '../api/useApi';
import { Box, Link, TextField, IconButton } from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import { debounce } from '../utils';
import EditPackageDialog from './EditPackageDialog';

interface PackageSearchTableProps {}

export interface Package {
  id: string;
  name: string;
  title: string;
  chatgpt_summary: string;
  author: string;
  organization: {
    title: string;
  };
  access_category: string;
  geo_span: string;
  notes: string;
  tags: Array<{ name: string }>;
  file_format: string;
  license_title: string;
  published_date: string;
  [key: string]: any;
}

const PackageSearchTable: React.FC<PackageSearchTableProps> = () => {
  const { api, executeApiCall } = useApi();
  const [packages, setPackages] = useState<Package[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [page, setPage] = useState<number>(0);
  const [pageSize, setPageSize] = useState<number>(25);
  const [rowCount, setRowCount] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [sortModel, setSortModel] = useState<GridSortModel>([]);
  const [filterModel, setFilterModel] = useState<GridFilterModel>({ items: [] });
  const [selectedPackage, setSelectedPackage] = useState<Package | null>(null);
  const [dialogOpen, setDialogOpen] = useState<boolean>(false);

  const debouncedFetchPackages = useCallback(
    debounce(async (query: string, start: number, rows: number, sortModel: GridSortModel, filterModel: GridFilterModel) => {
      setLoading(true);
      try {
        const sort = sortModel.length ? `${sortModel[0].field} ${sortModel[0].sort}` : '';
        const filters = filterModel.items.filter(item => !!item.value).map(item => `${item.field}:${item.value}`).join(' AND ');
        const result = await executeApiCall(() => api.packageSearch(query, rows, start, sort, filters));
        setPackages(result.results);
        setRowCount(result.count);
      } catch (error) {
        console.error('Failed to fetch packages:', error);
      } finally {
        setLoading(false);
      }
    }, 500),
    []
  );

  useEffect(() => {
    debouncedFetchPackages(searchQuery, page * pageSize, pageSize, sortModel, filterModel);
  }, [page, pageSize, searchQuery, sortModel, filterModel, debouncedFetchPackages]);

  const handleSearch = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(event.target.value);
    setPage(0);
  };

  const handlePaginationChange = (model: GridPaginationModel) => {
    setPage(model.page);
    setPageSize(model.pageSize);
  };

  const handleSortModelChange = (model: GridSortModel) => {
    setSortModel(model);
  };

  const handleFilterModelChange = (model: GridFilterModel) => {
    setFilterModel(model);
  };

  const handleEditClick = (pkg: Package) => {
    setSelectedPackage(pkg);
    setDialogOpen(true);
  };

  const handleDialogClose = () => {
    setDialogOpen(false);
    setSelectedPackage(null);
  };

  const containsFilter = getGridStringOperators().filter(op => op.value === 'contains');
  const columns: GridColDef[] = useMemo(() => [
    { field: 'id', headerName: 'ID', width: 150 },
    {
      field: 'name',
      headerName: 'Name',
      width: 200,
      renderCell: (params) => (
        <Link href={`/catalogue/${params.row.id}`} target="_blank" rel="noopener">
          {params.value}
        </Link>
      ),
      sortable: true,
      filterOperators: containsFilter
    },
    { field: 'title', headerName: 'Title', width: 200, sortable: true, filterOperators: containsFilter },
    {
      field: 'chatgpt_summary',
      headerName: 'Summary',
      width: 300,
      sortable: false,
      filterOperators: containsFilter,
      renderCell: (params) => (
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <IconButton onClick={() => handleEditClick(params.row)}>
            <EditIcon />
          </IconButton>
          <span>{params.value}</span>
        </Box>
      )
    },
    { field: 'author', headerName: 'Author', width: 200, sortable: true, filterOperators: containsFilter },
    { 
      field: 'organization.title', 
      headerName: 'Organization', 
      width: 200, 
      sortable: true, 
      filterOperators: containsFilter,
      renderCell: (params) => params.row.organization?.title || ''
    },
    { field: 'access_category', headerName: 'Access Category', width: 150, sortable: true, filterOperators: containsFilter },
    { field: 'geo_span', headerName: 'Geographical Span', width: 150, sortable: true, filterOperators: containsFilter },
    { field: 'notes', headerName: 'Notes', width: 300, sortable: true, filterOperators: containsFilter },
    { field: 'tags', headerName: 'Tags', width: 200, sortable: true, filterOperators: containsFilter, renderCell: (params) => params.value.map((tag: any) => tag.name).join(', ') },
    { field: 'file_format', headerName: 'File Format', width: 150, sortable: true, filterOperators: containsFilter },
    { field: 'license_title', headerName: 'License', width: 150, sortable: true, filterOperators: containsFilter },
    { field: 'published_date', headerName: 'Published Date', width: 150, sortable: true, filterOperators: containsFilter },
    // Add more columns as necessary
  ], []);

  return (
    <Box sx={{ height: 650, width: '100%' }} maxWidth={"xl"}>
      <TextField
        label="Search"
        variant="outlined"
        onChange={handleSearch}
        style={{ marginBottom: '10px', width: '100%' }}
      />
      <DataGrid
        rows={packages}
        columns={columns}
        pagination
        paginationMode="server"
        rowCount={rowCount}
        pageSizeOptions={[25, 50, 100]}
        paginationModel={{ page, pageSize }}
        onPaginationModelChange={handlePaginationChange}
        sortingMode="server"
        sortModel={sortModel}
        onSortModelChange={handleSortModelChange}
        filterMode="server"
        filterModel={filterModel}
        onFilterModelChange={handleFilterModelChange}
        loading={loading}
        getRowId={(row) => row.id}
      />
      <EditPackageDialog
        open={dialogOpen}
        handleClose={handleDialogClose}
        packageData={selectedPackage}
      />
    </Box>
  );
};

export default PackageSearchTable;
