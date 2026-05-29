'use client';

import { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider, CssBaseline } from '@mui/material';
import { SnackbarProvider } from 'notistack';
import { AuthProvider } from '../context/AuthContext';
import { DataGodThemeProvider, useThemeMode } from '../context/ThemeContext';
import './global.css';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: (failureCount: number, error: any) => {
        const status = error?.response?.status;
        if (status && status >= 400 && status < 500) return false;
        return failureCount < 1;
      },
      refetchOnWindowFocus: false,
    },
  },
});

interface RootLayoutProps {
  children: ReactNode;
}

// Inner component that uses the theme from context
function ThemedApp({ children }: { children: ReactNode }) {
  const { theme } = useThemeMode();

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <SnackbarProvider
        maxSnack={3}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        autoHideDuration={4000}
      >
        <AuthProvider>
          {children}
        </AuthProvider>
      </SnackbarProvider>
    </ThemeProvider>
  );
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="description" content="DataGod - Public Records Data Platform" />
        <meta name="color-scheme" content="light dark" />
        <title>DataGod - Public Records Data Platform</title>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
        {/* Prevent flash of unstyled content */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var mode = localStorage.getItem('datagod-theme-mode');
                  if (!mode) {
                    mode = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
                  }
                  document.documentElement.setAttribute('data-theme', mode);
                  document.documentElement.style.colorScheme = mode;
                } catch (e) {}
              })();
            `,
          }}
        />
      </head>
      <body>
        <QueryClientProvider client={queryClient}>
          <DataGodThemeProvider>
            <ThemedApp>
              {children}
            </ThemedApp>
          </DataGodThemeProvider>
        </QueryClientProvider>
      </body>
    </html>
  );
}
