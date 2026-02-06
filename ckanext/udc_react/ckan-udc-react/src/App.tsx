import React, { Suspense, lazy } from 'react';
import './App.css'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import Footer from './base/footer'
import { AuthProvider } from './api/authContext';
import { CircularProgress, Container } from '@mui/material';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import FAQPage from './tutorial/FAQPage';
import RequestOrganizationAccess from './requestOrgAccess/RequestOrganizationAccess';
import ApproveRequest from './requestOrgAccess/ApproveRequest';
import { REACT_PATH } from './constants';

const DrawerDashboard = lazy(() => import('./dashboard/drawer'));


export default function App() {
  const theme = createTheme({
    components: {
      MuiButton: {
        styleOverrides: {
          root: {
            textTransform: 'none',
          },
        },
      },
    },
  });

  let router = createBrowserRouter([
    {
      path: `/${REACT_PATH}/faq/:faqId?/*`,
      Component() {
        return <Suspense fallback={
          <Container sx={{ minHeight: '80%', padding: 4, textAlign: 'center' }}>
            <CircularProgress />
          </Container>}>
          <FAQPage />
        </Suspense>

      },
    },
    {
      path: `/${REACT_PATH}/request-organization-access/token/:token`,
      Component() {
        return <AuthProvider dismissable={false}><ApproveRequest /></AuthProvider>
      },
    },
    {
      path: `/${REACT_PATH}/request-organization-access/:option?`,
      Component() {
        return <AuthProvider dismissable={false}><RequestOrganizationAccess /></AuthProvider>
      },
    },
    {
      path: "/*",
      Component() {
        return <Suspense fallback={
          <Container sx={{ minHeight: '80%', padding: 4, textAlign: 'center' }}>
            <CircularProgress />
          </Container>}>
          <AuthProvider><DrawerDashboard /></AuthProvider>
        </Suspense>

      },
    },
  ]);

  return (
    <ThemeProvider theme={theme}>
      <RouterProvider router={router} fallbackElement={<p>Loading...</p>} />
      <Footer />
    </ThemeProvider>
  );
}
