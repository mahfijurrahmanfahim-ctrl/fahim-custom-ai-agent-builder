import './globals.css';
import type { Metadata } from 'next';
export const metadata: Metadata = { title: 'FAHIM AUTOPILOT AI', description: 'Your client research and outreach approval workspace.' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body>{children}</body></html>; }
