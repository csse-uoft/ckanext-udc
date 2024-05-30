import './App.css'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import DrawerDashboard from './dashboard/drawer'
import QAPage from './qa/QAPage'
import Footer from './base/footer'
import { AuthProvider } from './api/authContext';

export default function App() {

  let router = createBrowserRouter([
    {
      path: "/udc-react/qa",
      Component: () => <QAPage />

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
