# Digital Wellbeing — Official Website

This directory contains the source code for the official landing page and documentation site for **Digital Wellbeing for Windows**, hosted at [digitalwellbeing.vercel.app](https://digitalwellbeing.vercel.app).

Built with **Next.js 15 (App Router)**, **Tailwind CSS**, and **TypeScript**.

---

## Getting Started

### 1. Install Dependencies
```bash
npm install
```

### 2. Run the Development Server
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to view the site.

### 3. Build for Production
```bash
npm run build
```

---

## Project Structure

- `src/app/`: Next.js App Router pages and API routes (`/api/download`, `/api/stats`).
- `src/components/`:
  - `interactive/`: Capabilities canvas and interactive focus mode previews.
  - `layout/`: Navbar, footer, and container primitives.
  - `ui/`: Lightbox, buttons, stats cards, and theme widgets.
- `src/config/site.ts`: Site-wide branding configuration and download links.
- `public/`: Static images, screenshots, logos, and app icons.
