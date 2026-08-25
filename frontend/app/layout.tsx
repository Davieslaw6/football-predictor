import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "./theme-context";
import { Analytics } from "@vercel/analytics/next";

export const metadata: Metadata = {
  title: "Fulltime — Football Match Intelligence",
  description: "Football match prediction and analysis powered by form, Elo, head-to-head history, and goal expectancy.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning data-theme="dark">
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var stored = localStorage.getItem('theme');
                  var theme = stored || (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
                  document.documentElement.setAttribute('data-theme', theme);
                } catch (e) {}
              })();
            `,
          }}
        />
      </head>
      <body className="min-h-full antialiased">
        <ThemeProvider>
          <div className="floodlight" />
          <div className="relative z-10">{children}</div>
        </ThemeProvider>
        <Analytics />
      </body>
    </html>
  );
}
