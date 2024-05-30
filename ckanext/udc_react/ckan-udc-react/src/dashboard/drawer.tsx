import React, { useState, useEffect } from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { Box, CssBaseline, Drawer, List, ListItemIcon, ListItemText, Divider, Collapse, Toolbar, Typography, Breadcrumbs, ListItemButton } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import ExpandLess from '@mui/icons-material/ExpandLess';
import ExpandMore from '@mui/icons-material/ExpandMore';
import IconButton from '@mui/material/IconButton';
import drawerConfig, { DrawerGroup } from './drawerConfig'; // Import the TS configuration

const drawerWidth = 240;

const DrawerDashboard: React.FC = () => {
  const [drawerOpen, setDrawerOpen] = useState(true);
  const [drawerGroups, setDrawerGroups] = useState<DrawerGroup[]>([]);
  const [openGroups, setOpenGroups] = useState<{ [key: number]: boolean }>({});
  const location = useLocation();

  useEffect(() => {
    // Load the drawer configuration from the TS object
    setDrawerGroups(drawerConfig.groups);

    // Initialize open state for each group
    const initialOpenGroups: { [key: number]: boolean } = {};
    drawerConfig.groups.forEach((group, index) => {
      initialOpenGroups[index] = true;
    });
    setOpenGroups(initialOpenGroups);
  }, []);

  const toggleDrawer = () => {
    setDrawerOpen(!drawerOpen);
  };

  const toggleGroup = (index: number) => {
    setOpenGroups({ ...openGroups, [index]: !openGroups[index] });
  };

  const getBreadcrumbs = (): { text: string, path?: string }[] | null => {
    const path = location.pathname;
    for (const group of drawerGroups) {
      for (const item of group.items) {
        if (item.path === path) {
          return [
            { text: group.title },
            { text: item.text, path }
          ];
        }
      }
    }
    return null;
  };

  const breadcrumbs = getBreadcrumbs();

  return (
    <Box sx={{ display: 'flex'}}>
      {/* <CssBaseline /> */}
      <Drawer
        variant="permanent"
        sx={{
          width: drawerOpen ? drawerWidth : 0,
          flexShrink: 0,
          transition: 'width 0.3s',
          '& .MuiDrawer-paper': {
            width: drawerOpen ? drawerWidth : 0,
            boxSizing: 'border-box',
            position: 'relative',
            transition: 'width 0.3s',
            overflowX: 'hidden'
          },
        }}
      >
        <Divider />
        {drawerGroups.map((group, index) => (
          <React.Fragment key={group.title}>
            <List>
              <ListItemButton onClick={() => toggleGroup(index)}>
                <ListItemText primary={group.title} sx={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} />
                {openGroups[index] ? <ExpandLess /> : <ExpandMore />}
              </ListItemButton>
              <Collapse in={openGroups[index]} timeout="auto" unmountOnExit>
                {group.items.map((item) => (
                  <ListItemButton key={item.text} component={Link} to={item.path}>
                    <ListItemIcon>
                      {item.icon}
                    </ListItemIcon>
                    <ListItemText primary={item.text} sx={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} />
                  </ListItemButton>
                ))}
              </Collapse>
            </List>
            {index < drawerGroups.length - 1 && <Divider />}
          </React.Fragment>
        ))}
      </Drawer>
      <Box
        component="main"
        sx={{
          flexGrow: 2,
          bgcolor: 'background.default',
          p: 1,
          display: 'flex',
          flexDirection: 'column',
          minHeight: '100vh'
        }}
      >
        <Toolbar sx={{ flexShrink: 0 }}>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={toggleDrawer}
            sx={{ mr: 2 }}
          >
            <MenuIcon />
          </IconButton>
          {breadcrumbs && (
            <Breadcrumbs aria-label="breadcrumb">
              {breadcrumbs.map(breadcrumb => (
                breadcrumb.path ? (
                  <Link key={breadcrumb.path} to={breadcrumb.path}>
                    {breadcrumb.text}
                  </Link>
                ) : (
                  <Typography key={breadcrumb.text}>
                    {breadcrumb.text}
                  </Typography>
                )
              ))}
            </Breadcrumbs>
          )}
        </Toolbar>
        <Box sx={{ flexGrow: 1 }}>
          <Routes>
            {drawerGroups.flatMap(group =>
              group.items.map(item => (
                <Route key={item.path} path={item.path} element={<item.component />} />
              ))
            )}
          </Routes>
        </Box>
      </Box>
    </Box>
  );
};

export default DrawerDashboard;
