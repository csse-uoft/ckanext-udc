import { Container, Paper, Box, InputLabel, FormControl, Button, Divider, } from '@mui/material';
import Grid from '@mui/material/Unstable_Grid2'; // Grid version 2
import DynamicTabs, { IDynamicTab } from './tabs';

import CodeMirror from "@uiw/react-codemirror";
import { python } from '@codemirror/lang-python';
import { BootstrapTextField } from './inputs';
import { useEffect, useState } from 'react';
import { deleteImportConfig, getImportConfigs, updateImportConfig, runImport } from '../api';
import { Add, SaveOutlined, PlayArrowOutlined, DeleteForeverOutlined } from '@mui/icons-material';

export type IImportConfig = { uuid?: string, code: string, name: string }[];

export interface ImportPanelProps {
  defaultUUID?: string;
  defaultName?: string;
  defaultCode?: string;
  onUpdate: (option?: string) => void
}

function ImportPanel(props: ImportPanelProps) {

  const [importConfig, setImportConfig] = useState({
    uuid: props.defaultUUID,
    name: props.defaultName ?? "",
    code: props.defaultCode ?? "",
  });

  const handleChange = (field: string) => (e: any) => {
    setImportConfig(initials => ({
      ...initials,
      [field]: e.target.value
    }));
  }

  const handleChangeCode = (code: string) => {
    setImportConfig(initials => ({
      ...initials,
      code,
    }));
  }

  const handleSave = async () => {
    try {
      await updateImportConfig(importConfig);
      props.onUpdate();
    } catch (e) {
      console.error(e)
    }
  }

  const handleSaveAndRun = async () => {
    try {
      const { result } = await updateImportConfig(importConfig);
      if (result?.id) {
        await runImport(result.id)
        // show import status
        props.onUpdate('show-status');
      }

    } catch (e) {
      console.error(e)
    }
  }

  const handleDelete = async () => {
    try {
      if (importConfig.uuid)
        await deleteImportConfig(importConfig.uuid)
      props.onUpdate();
    } catch (e) {
      console.error(e)
    }
  }


  return <>
    {/* <Button variant="outlined" color="success" sx={{ textTransform: "none", mb: 1}} startIcon={<Add/>}>
            Create new import
        </Button> */}
    <Paper variant='outlined' sx={{ p: 3 }}>
      <Grid container spacing={2}>
        <Grid xs={8}>
          <BootstrapTextField label="Import Name" value={importConfig.name}
            handleChange={handleChange("name")} helperText={importConfig.uuid && 'UUID: ' + importConfig.uuid} />
        </Grid>
        <Grid xs={12}>
          <FormControl variant="standard" fullWidth>
            <InputLabel shrink sx={{ fontSize: "18px", fontWeight: 600, mb: 10 }}>
              Python code snippets
            </InputLabel>
            <Box sx={{ pt: 3, minHeight: 424 }}>
              <CodeMirror
                value={importConfig.code}
                height="400px"
                onChange={handleChangeCode}
                extensions={[python()]}
              />
            </Box>
          </FormControl>

        </Grid>


        <Grid xs={12}>
          <Divider />
        </Grid>

        <Grid>
          <Button variant="outlined" startIcon={<SaveOutlined />} sx={{ textTransform: "none" }} onClick={handleSave}>
            Save
          </Button>
        </Grid>
        <Grid>
          <Button variant="outlined" color="success" startIcon={<PlayArrowOutlined />} sx={{ textTransform: "none" }} onClick={handleSaveAndRun}>
            Save and Run Import
          </Button>
        </Grid>
        {importConfig.uuid && <Grid>
          <Button variant="outlined" startIcon={<DeleteForeverOutlined />} color="error" sx={{ textTransform: "none" }} onClick={handleDelete}>Delete</Button>
        </Grid>}

      </Grid>

    </Paper>


  </>
}

export default function ImportDashboard() {

  const [tabs, setTabs] = useState<IDynamicTab[]>([]);

  const load = async (option?: string) => {
    const importConfigs: IImportConfig = await getImportConfigs();
    const newTabs = [];
    for (const [uuid, { code, name }] of Object.entries(importConfigs)) {
      newTabs.push({
        key: uuid, label: name, panel: <ImportPanel defaultUUID={uuid} defaultCode={code} defaultName={name} onUpdate={requestRefresh} />
      })
    }
    newTabs.push({ key: "new-import", label: "New Import", panel: <ImportPanel onUpdate={requestRefresh} /> });
    setTabs(newTabs);
  }
  const requestRefresh = () => {
    load();
  }

  useEffect(() => {
    load();
  }, []);

  // return <CUDCAdminDrawer>
  //         <DynamicTabs tabs={tabs} />
  //     </CUDCAdminDrawer>

  return <Container>
    <DynamicTabs tabs={tabs} />
  </Container>

}