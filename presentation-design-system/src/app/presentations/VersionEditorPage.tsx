import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  Box,
  Button,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import {
  presentationApi,
  type SlideTemplate,
  type VersionDetail,
} from '@/lib/presentationApi';

export function VersionEditorPage() {
  const { deckId, versionId } = useParams<{ deckId: string; versionId: string }>();
  const [version, setVersion] = useState<VersionDetail | null>(null);
  const [templates, setTemplates] = useState<SlideTemplate[]>([]);
  const [pickTemplate, setPickTemplate] = useState('');
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!versionId) return;
    setMsg(null);
    const v = await presentationApi.getVersion(versionId);
    setVersion(v);
  }, [versionId]);

  useEffect(() => {
    void presentationApi.listTemplates({ status: 'active' }).then(setTemplates).catch(() => {});
  }, []);

  useEffect(() => {
    void load().catch((e) => setMsg(String(e)));
  }, [load]);

  if (!deckId || !versionId) return null;

  const isDraft = version?.status === 'draft';

  return (
    <Box sx={{ p: 3, maxWidth: 1000, mx: 'auto' }}>
      <Stack direction="row" flexWrap="wrap" gap={1} sx={{ mb: 2 }}>
        <Button component={Link} to={`/presentations/${deckId}`}>
          ← Détail présentation
        </Button>
        <Button component={Link} to={`/presentations/${deckId}/versions/${versionId}/preview`} variant="contained" color="secondary">
          Prévisualiser (design)
        </Button>
      </Stack>
      {msg && (
        <Typography color="error" sx={{ mb: 2 }}>
          {msg}
        </Typography>
      )}
      {version && (
        <>
          <Typography variant="h5" sx={{ mb: 1 }}>
            {version.version_label} — {version.status}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {version.slides.length} slide(s) · brouillon = édition autorisée
          </Typography>
          <Stack direction="row" flexWrap="wrap" gap={1} sx={{ mb: 3 }}>
            <Button
              variant="outlined"
              disabled={!isDraft}
              onClick={() =>
                presentationApi.saveDraft(versionId, {}).then(setVersion).catch((e) => setMsg(String(e)))
              }
            >
              Save draft
            </Button>
            <Button
              variant="outlined"
              disabled={!isDraft}
              onClick={() =>
                presentationApi
                  .duplicateVersion(versionId)
                  .then(() => setMsg('Nouvelle version brouillon créée — retournez à la liste des versions.'))
                  .catch((e) => setMsg(String(e)))
              }
            >
              Save as new version
            </Button>
            <Button
              variant="contained"
              color="success"
              disabled={!isDraft}
              onClick={() => presentationApi.validateVersion(versionId).then(setVersion).catch((e) => setMsg(String(e)))}
            >
              Validate / Publish
            </Button>
            <Button
              variant="outlined"
              color="warning"
              onClick={() => presentationApi.archiveVersion(versionId).then(setVersion).catch((e) => setMsg(String(e)))}
            >
              Archive
            </Button>
            <Button
              variant="outlined"
              onClick={() => presentationApi.restoreVersion(versionId).then(setVersion).catch((e) => setMsg(String(e)))}
            >
              Restore
            </Button>
            <Button variant="outlined" onClick={() => presentationApi.setCurrentVersion(versionId).then(setVersion).catch((e) => setMsg(String(e)))}>
              Set current
            </Button>
          </Stack>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            Ajouter une slide (template actif)
          </Typography>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mb: 3 }}>
            <TextField
              select
              size="small"
              label="Template"
              value={pickTemplate}
              onChange={(e) => setPickTemplate(e.target.value)}
              sx={{ minWidth: 220 }}
            >
              {templates.map((t) => (
                <MenuItem key={t.id} value={t.id}>
                  {t.name} ({t.key})
                </MenuItem>
              ))}
            </TextField>
            <Button
              variant="contained"
              disabled={!isDraft || !pickTemplate}
              onClick={() =>
                presentationApi
                  .addSlide(versionId, pickTemplate)
                  .then(load)
                  .catch((e) => setMsg(String(e)))
              }
            >
              Insérer
            </Button>
          </Stack>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            Slides
          </Typography>
          <Stack spacing={1}>
            {version.slides.map((s) => (
              <Box key={s.id} sx={{ border: '1px solid #eee', borderRadius: 1, p: 1.5 }}>
                <Typography variant="body2" fontWeight={600}>
                  #{s.sort_order} · {s.template_key ?? s.slide_template_id}
                </Typography>
                <Typography component="pre" variant="caption" sx={{ whiteSpace: 'pre-wrap', mt: 1 }}>
                  {JSON.stringify(s.content_json, null, 2)}
                </Typography>
              </Box>
            ))}
          </Stack>
          {version.snapshot_json && (
            <Box sx={{ mt: 3 }}>
              <Typography variant="subtitle2">Snapshot (validée)</Typography>
              <Typography component="pre" variant="caption" sx={{ whiteSpace: 'pre-wrap' }}>
                {JSON.stringify(version.snapshot_json, null, 2).slice(0, 2000)}
                …
              </Typography>
            </Box>
          )}
        </>
      )}
    </Box>
  );
}
