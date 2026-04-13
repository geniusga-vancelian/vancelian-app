import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Box, Button, Stack, Typography } from '@mui/material';
import { presentationApi, type VersionSummary } from '@/lib/presentationApi';

export function PresentationDetailPage() {
  const { deckId } = useParams<{ deckId: string }>();
  const [deck, setDeck] = useState<Awaited<ReturnType<typeof presentationApi.getDeck>> | null>(null);
  const [versions, setVersions] = useState<VersionSummary[]>([]);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!deckId) return;
    setErr(null);
    try {
      const [d, v] = await Promise.all([presentationApi.getDeck(deckId), presentationApi.listVersions(deckId)]);
      setDeck(d);
      setVersions(v);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }, [deckId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!deckId) return null;

  return (
    <Box sx={{ p: 3, maxWidth: 900, mx: 'auto' }}>
      <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
        <Button component={Link} to="/presentations" variant="text">
          ← Liste
        </Button>
      </Stack>
      {err && (
        <Typography color="error" sx={{ mb: 2 }}>
          {err}
        </Typography>
      )}
      {deck && (
        <>
          <Typography variant="h5" sx={{ mb: 1 }}>
            {deck.name}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Slug : {deck.slug} · Courante : {deck.current_version_id ?? '—'}
          </Typography>
          <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
            <Button
              variant="outlined"
              size="small"
              onClick={() =>
                presentationApi
                  .duplicateVersion(deck.current_version_id!)
                  .then(load)
                  .catch((e) => setErr(String(e)))
              }
              disabled={!deck.current_version_id}
            >
              Dupliquer version courante
            </Button>
            <Button
              variant="outlined"
              size="small"
              color="warning"
              onClick={() => presentationApi.archiveVersion(deck.current_version_id!).then(load).catch((e) => setErr(String(e)))}
              disabled={!deck.current_version_id}
            >
              Archiver version courante
            </Button>
          </Stack>
        </>
      )}
      <Typography variant="subtitle1" sx={{ mb: 1 }}>
        Versions
      </Typography>
      <Stack spacing={1}>
        {versions.map((v) => (
          <Stack
            key={v.id}
            direction="row"
            alignItems="center"
            justifyContent="space-between"
            sx={{ border: '1px solid #e0e0e0', borderRadius: 1, p: 1.5 }}
          >
            <Box>
              <Typography fontWeight={600}>
                {v.version_label} (#{v.version_number}) — {v.status}
                {v.is_current ? ' · courante' : ''}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {new Date(v.updated_at).toLocaleString()}
              </Typography>
            </Box>
            <Stack direction="row" spacing={1}>
              <Button component={Link} to={`/presentations/${deckId}/versions/${v.id}/preview`} variant="outlined" size="small">
                Prévisualiser
              </Button>
              <Button component={Link} to={`/presentations/${deckId}/versions/${v.id}/edit`} variant="contained" size="small">
                Éditer
              </Button>
            </Stack>
          </Stack>
        ))}
      </Stack>
    </Box>
  );
}
