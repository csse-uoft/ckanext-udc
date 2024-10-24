import React, { Suspense, lazy } from 'react';
import './App.css'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import QAPage from './qa/QAPage'
import Footer from './base/footer'
import { AuthProvider } from './api/authContext';
import CreateCatalogueEntry from './tutorial/CreateCatalogueEntry'
import { CircularProgress, Container } from '@mui/material';
import FAQPage from './tutorial/FAQPage';

const DrawerDashboard = lazy(() => import('./dashboard/drawer'));


export default function App() {

  let router = createBrowserRouter([
    {
      path: "/udc-react/faq/:faqId?/*",
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

  return <>
    <RouterProvider router={router} fallbackElement={<p>Loading...</p>} />
    <Footer />
  </>;
}
