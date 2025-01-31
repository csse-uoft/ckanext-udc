// PackageSearchTable.tsx
import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { DataGrid, GridColDef, GridPaginationModel, GridSortModel, GridFilterModel, getGridStringOperators, getGridSingleSelectOperators, GridToolbar, GridRowSelectionModel } from '@mui/x-data-grid';
import { useApi } from '../api/useApi';
import { Box, Link, TextField, IconButton, Checkbox, FormControlLabel } from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import { debounce } from '../utils';
import EditPackageDialog from './EditPackageDialog';
import { useCustomToolbar } from './TableToolbar';
import TaskDialog, { Task } from './Tasks';

interface PackageSearchTableProps { }

interface Organization {
  id: string;
  name?: string;
  title: string;
}

export interface Package {
  id: string;
  name: string;
  title: string;
  chatgpt_summary: string;
  author: string;
  organization: Organization
  access_category: string;
  geo_span: string;
  notes: string;
  tags: Array<{ name: string }>;
  file_format: string;
  license_title: string;
  published_date: string;
  [key: string]: any;
}

const buildFilters = (filterModel: GridFilterModel, emptySummaryOnly: boolean) => {
  const fq: string[] = [];
  filterModel.items.forEach(item => {
    if (item) {
      fq.push(`${item.field}:${item.value}`);
    }
  });
  if (emptySummaryOnly) {
    fq.push("-chatgpt_summary:[* TO *]");
  }
  return fq.join(' AND ');
};

const buildSorts = (sortModel: GridSortModel) => {
  const sorts = [];
  for (const sort of sortModel) {
    if (sort.field === 'title') {
      sorts.push(`title_string+${sort.sort}`);
    } else {
      sorts.push(`${sort.field}+${sort.sort}`);
    }
  }
  return sorts.join(',');
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
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [selectedRows, setSelectedRows] = useState<GridRowSelectionModel>([]);

  const [queue, setQueue] = useState<Task[]>([]);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [openTasksDialog, setOpenTasksDialog] = useState<boolean>(false);

  const [emptySummaryOnly, setOnlyNoSummary] = useState<boolean>(false);

  const constomToolbar = useCustomToolbar({
    onGenerateSummary: async () => {
      console.log('Generate Summary');
      const newTasks: Task[] = [];
      for (const id of selectedRows) {
        const pkg = packages.find(pkg => pkg.id === id);
        if (!pkg) continue;
        if (queue.find(task => task.id === id)) continue;

        const task: Task = {
          id: id as string,
          title: pkg?.title || '',
          summary: pkg?.chatgpt_summary || '',
          status: 'pending'
        }
        newTasks.push(task);
      }
      setQueue(tasks => [...tasks, ...newTasks]);
      setOpenTasksDialog(true);
    },
    onClickShowTasks: () => {
      setOpenTasksDialog(true);
    }
  });

  useEffect(() => {
    if (isProcessing || queue.length === 0) return;
    setIsProcessing(true);

    const processNextJob = async () => {
      // Find the first pending job
      const nextPendingJobIdx = queue.findIndex(job => job.status === 'pending');
      if (nextPendingJobIdx === -1) {
        setIsProcessing(false);
        return;
      }

      const job = queue[nextPendingJobIdx];
      job.status = 'processing';
      setQueue((prevQueue) => [...prevQueue]);

      try {
        const result = await executeApiCall(() => api.generateSummary(job.id));
        job.summary = result.results[0];

        // Update the package in the table
        const pkg_ = packages.find(pkg => pkg.id === job.id);
        if (pkg_) {
          pkg_.chatgpt_summary = job.summary;
          setPackages((prevPackages) => [...prevPackages]);
        }
        // Get the package and update the summary
        const pkg = await executeApiCall(() => api.packageShow(job.id));
        pkg.chatgpt_summary = job.summary;
        await executeApiCall(() => api.updatePackage(job.id, pkg));

        job.status = 'success';
      } catch (error) {
        job.status = 'failed';
        console.error('Failed to generate summary:', error);
      }

      job.status = 'success';
      setQueue((prevQueue) => [...prevQueue]);
      setIsProcessing(false);
    };
    processNextJob();

  }, [queue, isProcessing]);

  const debouncedFetchPackages = useCallback(
    debounce(async (query: string, start: number, rows: number, sortModel: GridSortModel, filterModel: GridFilterModel, emptySummaryOnly: boolean) => {
      setLoading(true);
      try {
        const sort = buildSorts(sortModel);
        console.log('Sort:', sort, sortModel);
        let filters = buildFilters(filterModel, emptySummaryOnly);
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
    // Get all organizations
    (async function () {
      const result = await executeApiCall(() => api.getOrganizationsAndAdmins());
      setOrganizations(result.organizations.map(org => ({ id: org.id, title: org.name })));
    })();

    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      if (isProcessing) {
        event.returnValue = "Are you sure you want to leave? Any pending tasks will be lost.";
      }
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };

  }, []);

  useEffect(() => {
    debouncedFetchPackages(searchQuery, page * pageSize, pageSize, sortModel, filterModel, emptySummaryOnly);
  }, [page, pageSize, searchQuery, sortModel, filterModel, emptySummaryOnly, debouncedFetchPackages]);

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
    console.log('Filter model:', model);
    setFilterModel(model);
  };

  const handleEditClick = (pkg: Package) => {
    setSelectedPackage(pkg);
    setDialogOpen(true);
  };

  const handleRowSelection = (selectedRows: GridRowSelectionModel) => {
    setSelectedRows(selectedRows);
  }

  const handleEditDialogClose = (pkg?: Package) => {
    if (pkg && selectedPackage) {
      selectedPackage.chatgpt_summary = pkg.chatgpt_summary;
      setPackages([...packages]);
    }
    console.log(pkg)
    setDialogOpen(false);
    setSelectedPackage(null);
  };

  const handleClearTasks = () => {
    setQueue([]);
  };

  const containsFilter = getGridStringOperators().filter(op => op.value === 'contains');
  // const eqFilter = 	
  const columns: GridColDef[] = useMemo(() => [
    { field: 'id', headerName: 'ID', width: 80 },
    {
      field: 'name',
      headerName: 'Name',
      width: 100,
      renderCell: (params) => (
        <Link href={`/catalogue/${params.row.id}`} target="_blank" rel="noopener">
          {params.value}
        </Link>
      ),
      sortable: true,
      filterOperators: containsFilter
    },
    { field: 'title', headerName: 'Title', width: 300, sortable: true, filterOperators: containsFilter },
    {
      field: 'organization',
      headerName: 'Organization',
      width: 200,
      sortable: true,
      filterOperators: getGridSingleSelectOperators(),
      renderCell: (params) => params.row.organization?.title || '',
      type: "singleSelect",
      valueOptions: organizations,
      getOptionValue: (value: Organization) => value.id,
      getOptionLabel: (value: Organization) => value.title,
    },
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
    { field: 'notes', headerName: 'Notes', width: 300, sortable: true, filterOperators: containsFilter },
    { field: 'tags', headerName: 'Tags', width: 200, sortable: true, filterOperators: containsFilter, renderCell: (params) => params.value.map((tag: any) => tag.name).join(', ') },
    { field: 'file_format', headerName: 'File Format', width: 150, sortable: true, filterOperators: containsFilter },
    { field: 'license_title', headerName: 'License', width: 150, sortable: true, filterOperators: containsFilter },
    { field: 'published_date', headerName: 'Published Date', width: 150, sortable: true, filterOperators: containsFilter },
    { field: 'author', headerName: 'Author', width: 200, sortable: true, filterOperators: containsFilter },
    { field: 'access_category', headerName: 'Access Category', width: 150, sortable: true, filterOperators: containsFilter },
    { field: 'geo_span', headerName: 'Geographical Span', width: 150, sortable: true, filterOperators: containsFilter },

    // Add more columns as necessary
  ], [organizations]);

  if (organizations.length === 0) {
    return <div>Loading...</div>;
  }

  return (
    <Box sx={{ height: 650, width: '100%' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
     
      <FormControlLabel
        control={
        <Checkbox
          checked={emptySummaryOnly}
          onChange={(e) => setOnlyNoSummary(e.target.checked)}
          color="primary"
        />
        }
        label="Empty summary only"
      />
       <TextField
        label="Search"
        variant="outlined"
        onChange={handleSearch}
        style={{ width: '60%' }}
      />
      </Box>
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
        checkboxSelection
        disableRowSelectionOnClick
        onRowSelectionModelChange={handleRowSelection}
        slots={{ toolbar: constomToolbar }}
      />
      <EditPackageDialog
        open={dialogOpen}
        handleClose={handleEditDialogClose}
        packageData={selectedPackage}
      />
      <TaskDialog open={openTasksDialog} tasks={queue} onClose={() => setOpenTasksDialog(false)} onClearTasks={handleClearTasks} />
    </Box>
  );
};

export default PackageSearchTable;
