import './globals.css';

export const metadata = {
  title: 'Cognita 🧠 — AI Study Companion',
  description: 'Your AI study companion that speaks, shows, and teaches. Upload PDFs, images, and notes — get voice explanations, summaries, and practice questions.',
  keywords: ['study', 'AI', 'tutor', 'exam prep', 'education', 'voice', 'PDF'],
  openGraph: {
    title: 'Cognita 🧠',
    description: 'Your AI study companion that speaks, shows, and teaches.',
    type: 'website',
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
