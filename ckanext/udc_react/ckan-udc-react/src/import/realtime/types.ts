export interface ImportLog {
  timestamp: string;
  message: string;
  level: string;
}

export interface ImportProgress {
  current: number;
  total: number;
}

export interface RunningJob {
  id: string;
  import_config_id: string;
  run_at: string;
  run_by: string;
  is_running: boolean;
}

export interface ImportPanelProps {
  uuid: string;
  defaultName?: string;
  defaultCode?: string;
  onUpdate: (option?: string) => void;
}

export interface FinishedPackage {
  type: 'created' | 'updated' | 'deleted' | 'errored';
  data: {
    id: string;
    name: string;
    title: string;
    logs?: string;
    duplications?: [{
      id: string;
      name: string;
      title: string;
      reason: string;
    }]
  };
}
