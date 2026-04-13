import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Box, Button, Checkbox, FormControlLabel, Stack, TextField, Typography } from '@mui/material';
import { presentationApi, type DeckSummary } from '@/lib/presentationApi';

export function PresentationsListPage() {
  const [decks, setDecks] = useState<DeckSummary[]>([]);
  const [includeArchived, setIncludeArchived] = useState(false);
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setErr(null);
    try {
      setDecks(await presentationApi.listDecks(includeArchived));
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }, [includeArchived]);

  useEffect(() => {
    void load();
  }, [load]);

  async function createDeck() {
    setErr(null);
    if (!name.trim() || !slug.trim()) {
      setErr('Nom et slug requis');
      return;
    }
    try {
      const d = await presentationApi.createDeck({ name: name.trim(), slug: slug.trim() });
      setName('');
      setSlug('');
      await load();
      window.location.href = `/presentations/${d.id}`;
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <Box sx={{ p: 3, maxWidth: 900, mx: 'auto' }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h5">Présentations</Typography>
        <Button component={Link} to="/presentation-templates" variant="outlined">
          Templates API
        </Button>
      </Stack>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 3 }}>
        <TextField label="Nom" size="small" value={name} onChange={(e) => setName(e.target.value)} />
        <TextField label="Slug" size="small" value={slug} onChange={(e) => setSlug(e.target.value)} placeholder="investor-deck-2026" />
        <Button variant="contained" onClick={() => void createDeck()}>
          Créer + V1 brouillon
        </Button>
      </Stack>
      <FormControlLabel
        control={<Checkbox checked={includeArchived} onChange={(_, v) => setIncludeArchived(v)} />}
        label="Inclure archivées"
        sx={{ mb: 2 }}
      />
      {err && (
        <Typography color="error" sx={{ mb: 2 }}>
          {err}
        </Typography>
      )}
      <Stack spacing={1}>
        {decks.map((d) => (
          <Stack
            key={d.id}
            direction="row"
            alignItems="center"
            justifyContent="space-between"
            sx={{ border: '1px solid #e0e0e0', borderRadius: 1, p: 1.5 }}
          >
            <Box>
              <Typography fontWeight={600}>{d.name}</Typography>
              <Typography variant="body2" color="text.secondary">
                {d.slug} · {d.deck_type ?? '—'} · maj {new Date(d.updated_at).toLocaleString()}
                {d.archived_at && ' · archivée'}
              </Typography>
            </Box>
            <Button component={Link} to={`/presentations/${d.id}`} variant="outlined" size="small">
              Ouvrir
            </Button>
          </Stack>
        ))}
      </Stack>
    </Box>
  );
}
