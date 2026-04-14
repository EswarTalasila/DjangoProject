# EEL Data Dashboard - Frontend

Next.js frontend for the EE Lab Data Dashboard.

## Stack

- Node.js 20+
- Next.js 14
- TypeScript
- Tailwind CSS
- React

## Frontend Structure

```
app/
├── (auth)/                  <-- Public Pages
│   ├── layout.tsx
│   └── login/
│       └── page.tsx
│
├── (dashboard)/             <-- Private Pages (Has Header)
│   ├── layout.tsx
│   ├── page.tsx
│   ├── dashboard/
│   │   ├── assignment-templates/
│   │   │   ├── page.tsx     <-- List of assignment templates
│   │   │   ├── new/
│   │   │   │   └── page.tsx
│   │   │   └── [id]/
│   │   │       ├── page.tsx
│   │   │       └── edit/
│   │   │           └── page.tsx
│   │   ├── assignments/
│   │   ├── courses/
│   │   ├── rubrics/
│   │   ├── submissions/
│   │   └── visualizations/
│
├── api/                     <-- Next.js API
├── favicon.ico
└── globals.css


```

## Local Development

### With Docker (recommended)

### Without Docker

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:8080](http://localhost:8080) with your browser to use the app through the local nginx proxy.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!
