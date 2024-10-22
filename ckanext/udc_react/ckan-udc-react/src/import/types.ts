import { CKANOrganization } from '../api/api';


export interface IImportConfig {
  [uuid: string]: {
    uuid?: string
    name: string;  // The name of the import task
    code: string;  // Some code or identifier related to the import task (e.g., configuration or script code)
  };
}
