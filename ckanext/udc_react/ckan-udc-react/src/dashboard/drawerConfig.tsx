import { CloudSync, Publish, Edit, OpenInBrowser, Settings, Replay, SystemSecurityUpdate } from '@mui/icons-material';
import ImportDashboard from '../import/ImportDashboard';
import { ImportStatus } from '../import/importStatus';
import QAPage from '../qa/QAPage';
import ConfigManagementPage from '../qa/ConfigManagementPage';
import ChatGPTSummarySettings from '../chatgptSummary/ChatGPTSummarySettings';
import ManagerSummary from '../chatgptSummary/ManageSummary';
import { RealtimeImportStatus } from '../import/realtime/RealtimeImportStatus';
import { REACT_PATH } from '../constants';
import UDRCConfigPage from '../udrc/Settings';
import SystemReload from '../udrc/SystemReload';
import CKANSystemStats from '../udrc/SystemStats';
import ManageLicenses from '../udrc/License/ManageLicenses';


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
          path: `/${REACT_PATH}/import`,
          component: ImportDashboard,
        },
        {
          text: "Import Status",
          icon: <CloudSync />,
          path: `/${REACT_PATH}/import-status`,
          component: ImportStatus,
        },
        {
          text: "Realtime Status",
          icon: <CloudSync />,
          path: `/${REACT_PATH}/realtime-status`,
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
          path: `/${REACT_PATH}/maturity-levels`,
          component: ConfigManagementPage,
        },
        {
          text: "Preview",
          icon: <OpenInBrowser />,
          path: `/${REACT_PATH}/maturity-levels/preview`,
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
          path: `/${REACT_PATH}/chatgpt-summary/manage`,
          component: ManagerSummary,
        },
        {
          text: "Settings",
          icon: <Settings />,
          path: `/${REACT_PATH}/chatgpt-summary/settings`,
          component: ChatGPTSummarySettings,
        }
      ]
    },
    {
      title: "UDRC System",
      items: [
        {
          text: "Manage Licenses",
          icon: <Settings />,
          path: `/${REACT_PATH}/system-config/licenses`,
          component: ManageLicenses,
        },
        {
          text: "System Config",
          icon: <Settings />,
          path: `/${REACT_PATH}/system-config/manage`,
          component: UDRCConfigPage,
        },
        {
          text: "Reload",
          icon: <Replay />,
          path: `/${REACT_PATH}/system-config/reload`,
          component: SystemReload,
        },
        {
          text: "Stats",
          icon: <SystemSecurityUpdate />,
          path: `/${REACT_PATH}/system-config/stats`,
          component: CKANSystemStats,
        }
      ]
    }
  ],

};

export default drawerConfig;