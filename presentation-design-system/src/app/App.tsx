import type { ReactNode } from 'react';
import { BrowserRouter, Link, Route, Routes } from 'react-router-dom';
import { Box, CssBaseline, Stack, ThemeProvider, createTheme } from '@mui/material';
import { DesignSystemShowcase } from './DesignSystemShowcase';
import RegistrationDeck from './deck/RegistrationDeck';
import RiskComplianceRegistrationDeck from './deck/RiskComplianceRegistrationDeck';
import { SlideTemplatesGallery } from './templates/SlideTemplatesGallery';
import { PresentationsListPage } from './presentations/PresentationsListPage';
import { PresentationDetailPage } from './presentations/PresentationDetailPage';
import { VersionEditorPage } from './presentations/VersionEditorPage';
import { PresentationVersionPreviewPage } from './presentations/PresentationVersionPreviewPage';
import { TemplatesRegistryPage } from './presentations/TemplatesRegistryPage';

const muiTheme = createTheme({
  palette: { mode: 'light' },
});

function AppShell({ children }: { children: ReactNode }) {
  return (
    <Box sx={{ minHeight: '100vh', bgcolor: '#fafafa' }}>
      <Box
        component="nav"
        sx={{
          px: 2,
          py: 1,
          borderBottom: '1px solid #e0e0e0',
          bgcolor: '#fff',
          fontSize: 14,
        }}
      >
        <Stack direction="row" gap={2} flexWrap="wrap" alignItems="center">
          <Link to="/">Registration deck</Link>
          <Link to="/templates">Galerie templates</Link>
          <Link to="/design-system">Design system</Link>
          <Link to="/presentations">Présentations (API)</Link>
          <Link to="/presentation-templates">Registre templates API</Link>
          <Link to="/deck/registration-risk-compliance">Deck LCB-FT × Registration</Link>
        </Stack>
      </Box>
      {children}
    </Box>
  );
}

export default function App() {
  return (
    <ThemeProvider theme={muiTheme}>
      <CssBaseline />
      <BrowserRouter>
        <AppShell>
          <Routes>
            <Route path="/" element={<RegistrationDeck />} />
            <Route path="/deck/registration-risk-compliance" element={<RiskComplianceRegistrationDeck />} />
            <Route path="/templates" element={<SlideTemplatesGallery />} />
            <Route path="/design-system" element={<DesignSystemShowcase />} />
            <Route path="/presentations" element={<PresentationsListPage />} />
            <Route path="/presentations/:deckId" element={<PresentationDetailPage />} />
            <Route path="/presentations/:deckId/versions/:versionId/edit" element={<VersionEditorPage />} />
            <Route path="/presentations/:deckId/versions/:versionId/preview" element={<PresentationVersionPreviewPage />} />
            <Route path="/presentation-templates" element={<TemplatesRegistryPage />} />
          </Routes>
        </AppShell>
      </BrowserRouter>
    </ThemeProvider>
  );
}
