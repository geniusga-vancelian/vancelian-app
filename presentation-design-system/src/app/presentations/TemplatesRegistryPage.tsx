import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Box, Button, MenuItem, Stack, TextField, Typography } from '@mui/material';
import { presentationApi, type SlideTemplate } from '@/lib/presentationApi';

export function TemplatesRegistryPage() {
  const [items, setItems] = useState<SlideTemplate[]>([]);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [status, setStatus] = useState('');
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setErr(null);
    try {
      const data = await presentationApi.listTemplates({
        search: search || undefined,
        category: category || undefined,
        status: status || undefined,
      });
      setItems(data);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }, [search, category, status]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <Box sx={{ p: 3, maxWidth: 1100, mx: 'auto' }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h5">Registre templates (API)</Typography>
        <Button component={Link} to="/presentations" variant="outlined">
          Présentations
        </Button>
      </Stack>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2 }}>
        <TextField label="Recherche" size="small" value={search} onChange={(e) => setSearch(e.target.value)} />
        <TextField label="Catégorie" size="small" value={category} onChange={(e) => setCategory(e.target.value)} />
        <TextField select label="Statut" size="small" value={status} onChange={(e) => setStatus(e.target.value)} sx={{ minWidth: 140 }}>
          <MenuItem value="">Tous</MenuItem>
          <MenuItem value="active">active</MenuItem>
          <MenuItem value="inactive">inactive</MenuItem>
          <MenuItem value="archived">archived</MenuItem>
        </TextField>
        <Button variant="contained" onClick={() => void load()}>
          Filtrer
        </Button>
      </Stack>
      {err && (
        <Typography color="error" sx={{ mb: 2 }}>
          {err}
        </Typography>
      )}
      <Stack spacing={1}>
        {items.map((t) => (
          <Stack
            key={t.id}
            direction={{ xs: 'column', sm: 'row' }}
            spacing={2}
            alignItems={{ sm: 'center' }}
            sx={{ border: '1px solid #e0e0e0', borderRadius: 1, p: 1.5 }}
          >
            <Box sx={{ flex: 1 }}>
              <Typography fontWeight={600}>
                {t.name}{' '}
                <Typography component="span" variant="body2" color="text.secondary">
                  ({t.key})
                </Typography>
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {t.category} · {t.status}
              </Typography>
              {t.description && (
                <Typography variant="body2" sx={{ mt: 0.5 }}>
                  {t.description}
                </Typography>
              )}
            </Box>
            <Stack direction="row" spacing={1}>
              {t.status !== 'archived' ? (
                <Button size="small" color="warning" onClick={() => presentationApi.archiveTemplate(t.id).then(load).catch((e) => setErr(String(e)))}>
                  Archiver
                </Button>
              ) : (
                <Button size="small" onClick={() => presentationApi.restoreTemplate(t.id).then(load).catch((e) => setErr(String(e)))}>
                  Restaurer
                </Button>
              )}
            </Stack>
          </Stack>
        ))}
      </Stack>
    </Box>
  );
}
