import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Research RAG',
  description: 'Academic PDF research assistant',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900 antialiased">{children}</body>
    </html>
  )
}
