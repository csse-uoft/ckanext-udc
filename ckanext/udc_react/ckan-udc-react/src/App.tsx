import './App.css'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import DrawerDashboard from './dashboard/drawer'
import QAPage from './qa/QAPage'
import Footer from './base/footer'
import { AuthProvider } from './api/authContext';
import CreateCatalogueEntry from './tutorial/CreateCatalogueEntry'

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
        return <AuthProvider><DrawerDashboard /></AuthProvider>;
      },
    },
  ]);

  return <>
    <RouterProvider router={router} fallbackElement={<p>Loading...</p>} />
    <Footer />
  </>;
}
