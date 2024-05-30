import './App.css'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import DrawerDashboard from './dashboard/drawer'
import QAPage from './qa/QAPage'
import Footer from './base/footer'

export default function App() {

  let router = createBrowserRouter([
    {
      path: "/udc-react/qa",
      Component: () => <QAPage />

    },
    {
      path: "/*",
      Component() {
        return <DrawerDashboard />;
      },
    },
  ]);

  return <>
    <RouterProvider router={router} fallbackElement={<p>Loading...</p>} />
    <Footer />
  </>;
}
