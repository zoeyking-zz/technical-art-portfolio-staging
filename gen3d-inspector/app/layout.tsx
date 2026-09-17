import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  metadataBase: new URL('https://gen3d-inspector.zoeyking0675.chatgpt.site'),
  title: 'Gen3D Inspector',
  description: 'A local-first multi-format 3D asset viewer and QA workbench.',
  openGraph: {
    title: 'Gen3D Inspector',
    description: 'Multi-format 3D asset viewer & QA workbench',
    type: 'website',
    images: [{ url: '/og.png', width: 1200, height: 630, alt: 'Gen3D Inspector — Multi-format 3D asset viewer and QA workbench' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Gen3D Inspector',
    description: 'Multi-format 3D asset viewer & QA workbench',
    images: ['/og.png'],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}

