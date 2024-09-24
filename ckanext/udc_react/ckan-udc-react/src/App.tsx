import React, { Suspense, lazy } from 'react';
import './App.css'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import QAPage from './qa/QAPage'
import Footer from './base/footer'
import { AuthProvider } from './api/authContext';
import CreateCatalogueEntry from './tutorial/CreateCatalogueEntry'
import { CircularProgress, Container } from '@mui/material';

const DrawerDashboard = lazy(() => import('./dashboard/drawer'));


export default function App() {

  let router = createBrowserRouter([
    {
      path: "/udc-react/tutorial/maturity-levels",
      Component: () => <QAPage />
    },
    {
      path: "/udc-react/tutorial/create-catalogue-entry",
      Component: () => <CreateCatalogueEntry />
    },
    {
      path: "/*",
      Component() {
        return <Suspense fallback={
        <Container sx={{ padding: 4, textAlign: 'center' }}>
          <CircularProgress />
        </Container>}>
          <AuthProvider><DrawerDashboard /></AuthProvider>
        </Suspense>

      },
    },
  ]);

  return <>
    <RouterProvider router={router} fallbackElement={<p>Loading...</p>} />
    <Footer />
  </>;
}
