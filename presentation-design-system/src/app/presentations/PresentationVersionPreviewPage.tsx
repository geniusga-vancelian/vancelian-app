import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { Link, useParams } from 'react-router-dom';
import { Box, Button, Stack, Typography } from '@mui/material';
import { presentationApi, type VersionDetail } from '@/lib/presentationApi';
import { ApiSlideRenderer } from './ApiSlideRenderer';
import { exportRegistrationDeckToPdf } from '../deck/exportRegistrationDeckToPdf';

function sortedSlides(v: VersionDetail) {
  return [...v.slides].sort((a, b) => a.sort_order - b.sort_order);
}

function safePdfFilePart(s: string) {
  return s.replace(/[^a-zA-Z0-9._-]+/g, '-').replace(/^-|-$/g, '') || 'presentation';
}

export function PresentationVersionPreviewPage() {
  const { deckId, versionId } = useParams<{ deckId: string; versionId: string }>();
  const [version, setVersion] = useState<VersionDetail | null>(null);
  const [deckSlug, setDeckSlug] = useState<string>('');
  const [err, setErr] = useState<string | null>(null);
  const [index, setIndex] = useState(0);
  const [pdfExporting, setPdfExporting] = useState(false);
  const [pdfProgress, setPdfProgress] = useState<{ current: number; total: number } | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const slideCaptureRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);

  const load = useCallback(async () => {
    if (!versionId || !deckId) return;
    setErr(null);
    try {
      const [v, d] = await Promise.all([
        presentationApi.getVersion(versionId),
        presentationApi.getDeck(deckId),
      ]);
      setVersion(v);
      setDeckSlug(d.slug);
      setIndex(0);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }, [versionId, deckId]);

  useEffect(() => {
    void load();
  }, [load]);

  const slides = version ? sortedSlides(version) : [];
  const total = slides.length;
  const isPublished = version?.status === 'validated';

  useLayoutEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const update = () => {
      const w = el.clientWidth;
      const pad = 32;
      setScale(Math.min(1, Math.max(0.2, (w - pad) / 1920)));
    };
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const go = useCallback(
    (delta: number) => {
      setIndex((i) => Math.max(0, Math.min(Math.max(0, total - 1), i + delta)));
    },
    [total],
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'PageDown') {
        e.preventDefault();
        go(1);
      }
      if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
        e.preventDefault();
        go(-1);
      }
      if (e.key === 'Home') {
        e.preventDefault();
        setIndex(0);
      }
      if (e.key === 'End') {
        e.preventDefault();
        setIndex(Math.max(0, total - 1));
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [go, total]);

  const handleDownloadPdf = useCallback(async () => {
    if (!isPublished || pdfExporting || total <= 0) return;
    const root = slideCaptureRef.current;
    if (!root) return;

    const previousIndex = index;
    setPdfExporting(true);
    setPdfProgress(null);
    flushSync(() => {
      setIndex(0);
    });

    await new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r())));
    await new Promise((r) => setTimeout(r, 200));

    const fileName = `${safePdfFilePart(deckSlug)}-${safePdfFilePart(version?.version_label ?? 'v')}.pdf`;

    try {
      await exportRegistrationDeckToPdf({
        captureRoot: root,
        slideCount: total,
        prepareSlide: (i) => {
          flushSync(() => setIndex(i));
        },
        fileName,
        onProgress: setPdfProgress,
        settleMs: 120,
      });
    } catch (e) {
      console.error(e);
      setErr(e instanceof Error ? e.message : 'Export PDF impossible.');
    } finally {
      flushSync(() => setIndex(previousIndex));
      setPdfExporting(false);
      setPdfProgress(null);
    }
  }, [deckSlug, index, isPublished, pdfExporting, total, version?.version_label]);

  if (!deckId || !versionId) return null;

  const currentSlide = total > 0 ? slides[index] : null;

  return (
    <Box className="flex min-h-screen flex-col bg-[#e5e5e5]">
      <Box
        component="header"
        sx={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 2,
          borderBottom: '1px solid #ccc',
          bgcolor: 'white',
          px: 2,
          py: 1.5,
        }}
      >
        <Stack direction="row" alignItems="center" gap={2} flexWrap="wrap">
          <Button component={Link} to={`/presentations/${deckId}/versions/${versionId}/edit`} size="small">
            ← Éditeur
          </Button>
          <Button component={Link} to={`/presentations/${deckId}`} size="small" variant="text">
            Détail présentation
          </Button>
          <Typography variant="caption" sx={{ color: '#1e1c1b' }}>
            Prévisualisation · {version?.version_label ?? '…'} ({version?.status ?? '…'}) · slide {total ? index + 1 : 0}/{total}
            {pdfProgress ? (
              <span style={{ marginLeft: 8, color: '#4F46E5' }}>
                PDF {pdfProgress.current}/{pdfProgress.total}
              </span>
            ) : null}
          </Typography>
        </Stack>
        <Stack direction="row" gap={1} flexWrap="wrap">
          {isPublished && total > 0 ? (
            <Button
              variant="contained"
              color="primary"
              disabled={pdfExporting}
              onClick={() => void handleDownloadPdf()}
            >
              {pdfExporting ? 'Génération PDF…' : 'Télécharger en PDF'}
            </Button>
          ) : (
            <Typography variant="caption" color="text.secondary" sx={{ alignSelf: 'center', maxWidth: 280 }}>
              PDF disponible après validation / publication de la version.
            </Typography>
          )}
        </Stack>
      </Box>

      {err && (
        <Typography color="error" sx={{ px: 2, py: 1 }}>
          {err}
        </Typography>
      )}

      <Box
        ref={containerRef}
        component="main"
        sx={{
          flex: 1,
          display: 'flex',
          justifyContent: 'center',
          overflow: 'auto',
          px: 2,
          py: 4,
          visibility: pdfExporting ? 'hidden' : 'visible',
        }}
        aria-hidden={pdfExporting}
      >
        {!version ? (
          <Typography>Chargement…</Typography>
        ) : total === 0 ? (
          <Typography>Aucune slide à afficher.</Typography>
        ) : currentSlide ? (
          <Box
            sx={{
              position: 'relative',
              flexShrink: 0,
              overflow: 'hidden',
              borderRadius: 0.5,
              boxShadow: 3,
              width: 1920 * scale,
              height: 1080 * scale,
            }}
          >
            <Box
              sx={{
                position: 'absolute',
                left: 0,
                top: 0,
                width: 1920,
                height: 1080,
                transform: `scale(${scale})`,
                transformOrigin: 'top left',
              }}
            >
              <ApiSlideRenderer slide={currentSlide} footerText="Vancelian — prévisualisation" />
            </Box>
          </Box>
        ) : null}
      </Box>

      <Box component="footer" sx={{ borderTop: '1px solid #ccc', bgcolor: 'white', px: 2, py: 2 }}>
        <Stack direction="row" flexWrap="wrap" alignItems="center" justifyContent="center" gap={2}>
          <Button disabled={index <= 0 || pdfExporting || total === 0} onClick={() => go(-1)}>
            Précédent
          </Button>
          <Stack direction="row" flexWrap="wrap" gap={0.5} justifyContent="center">
            {slides.map((s, j) => (
              <button
                key={s.id}
                type="button"
                disabled={pdfExporting}
                onClick={() => setIndex(j)}
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: '50%',
                  border: 'none',
                  cursor: pdfExporting ? 'default' : 'pointer',
                  background: j === index ? '#4F46E5' : '#d1d5db',
                }}
                aria-label={`Slide ${j + 1}`}
              />
            ))}
          </Stack>
          <Button disabled={index >= total - 1 || pdfExporting || total === 0} onClick={() => go(1)}>
            Suivant
          </Button>
        </Stack>
      </Box>

      {pdfExporting ? <Box sx={{ position: 'fixed', inset: 0, zIndex: 99998, bgcolor: 'rgba(0,0,0,0.45)' }} /> : null}
      <Box
        ref={slideCaptureRef}
        sx={{
          position: 'fixed',
          left: pdfExporting ? 0 : -12000,
          top: 0,
          zIndex: pdfExporting ? 99999 : 0,
          width: 1920,
          height: 1080,
          overflow: 'hidden',
          boxShadow: pdfExporting ? 4 : 0,
        }}
      >
        {pdfExporting && total > 0 ? (
          <ApiSlideRenderer slide={slides[index]} footerText="Vancelian" />
        ) : null}
      </Box>
      {pdfExporting ? (
        <Typography
          sx={{
            position: 'fixed',
            left: '50%',
            top: 24,
            zIndex: 100000,
            transform: 'translateX(-50%)',
            bgcolor: 'rgba(255,255,255,0.95)',
            px: 2,
            py: 1,
            borderRadius: 1,
            boxShadow: 2,
            fontSize: 14,
          }}
        >
          Génération du PDF…
        </Typography>
      ) : null}
    </Box>
  );
}
