import { useMemo, useState } from "react";
import {
  Box,
  List,
  ListItemButton,
  ListItemText,
  Paper,
  TextField,
  Typography,
} from "@mui/material";

export type ImportListItem = {
  id: string;
  name: string;
  subtitle?: string;
};

type ImportConfigListProps = {
  items: ImportListItem[];
  selectedId: string;
  onSelect: (id: string) => void;
  height?: number;
  filterPlaceholder?: string;
};

const ImportConfigList = ({
  items,
  selectedId,
  onSelect,
  height = 700,
  filterPlaceholder = "Filter imports",
}: ImportConfigListProps) => {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    if (!query.trim()) {
      return items;
    }
    const q = query.toLowerCase();
    return items.filter((item) => item.name.toLowerCase().includes(q));
  }, [items, query]);

  return (
    <Box>
      <TextField
        label={filterPlaceholder}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        fullWidth
        sx={{ mb: 2 }}
      />
      <Paper variant="outlined" sx={{ height, overflow: "auto" }}>
        {filtered.length === 0 ? (
          <Box sx={{ p: 2 }}>
            <Typography variant="body2" color="text.secondary">
              No imports found.
            </Typography>
          </Box>
        ) : (
          <List dense>
            {filtered.map((item) => (
              <ListItemButton
                key={item.id}
                selected={item.id === selectedId}
                onClick={() => onSelect(item.id)}
              >
                <ListItemText primary={item.name} secondary={item.subtitle} />
              </ListItemButton>
            ))}
          </List>
        )}
      </Paper>
    </Box>
  );
};

export default ImportConfigList;
