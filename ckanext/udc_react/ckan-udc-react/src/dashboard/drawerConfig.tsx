import { CloudSync, Publish, Edit, OpenInBrowser, Settings } from '@mui/icons-material';
import ImportDashboard from '../import/ImportDashboard';
import { ImportStatus } from '../import/importStatus';
import QAPage from '../qa/QAPage';
import ConfigManagementPage from '../qa/ConfigManagementPage';
import ChatGPTSummarySettings from '../chatgptSummary/ChatGPTSummarySettings';
import ManagerSummary from '../chatgptSummary/ManageSummary';
import { RealtimeImportStatus } from '../import/realtime/RealtimeImportStatus';


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
        },
        {
          text: "Realtime Status",
          icon: <CloudSync />,
          path: "/udc-react/realtime-status",
          component: RealtimeImportStatus,
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
    },
    {
      title: "ChatGPT Summary",
      items: [
        {
          text: "Manage Summary",
          icon: <Edit />,
          path: "/udc-react/chatgpt-summary/manage",
          component: ManagerSummary,
        },
        {
          text: "Settings",
          icon: <Settings/>,
          path: "/udc-react/chatgpt-summary/settings",
          component: ChatGPTSummarySettings,
        }
      ]
    }
  ],
  
};

export default drawerConfig;