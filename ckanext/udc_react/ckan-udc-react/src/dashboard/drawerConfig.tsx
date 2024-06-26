import { CloudSync, Publish, Edit, OpenInBrowser } from '@mui/icons-material';
import ImportDashboard from '../import/import';
import { ImportStatus } from '../import/importStatus';
import QAPage from '../qa/QAPage';
import ConfigManagementPage from '../qa/ConfigManagementPage';


export interface DrawerItem {
  text: string;
  icon: JSX.Element;
  path: string;
  component: React.FC;
}

export interface DrawerGroup {
  title: string;
  items: DrawerItem[];
}

export interface DrawerConfig {
  groups: DrawerGroup[];
}


const drawerConfig: DrawerConfig = {
  groups: [
    {
      title: "Import Management",
      items: [
        {
          text: "Import",
          icon: <Publish />,
          path: "/udc-react/import",
          component: ImportDashboard,
        },
        {
          text: "Import Status",
          icon: <CloudSync />,
          path: "/udc-react/import-status",
          component: ImportStatus,
        }
      ]
    },
    {
      title: "QA Page",
      items: [
        {
          text: "Maturity Levels",
          icon: <Edit />,
          path: "/udc-react/maturity-levels",
          component: ConfigManagementPage,
        },
        {
          text: "Preview",
          icon: <OpenInBrowser/>,
          path: "/udc-react/maturity-levels/preview",
          component: QAPage,
        }
      ]
    }
  ],
  
};

export default drawerConfig;