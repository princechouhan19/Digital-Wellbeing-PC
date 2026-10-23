# Deployment Guide for Digital Wellbeing Website

This website is built with Next.js 14 and is fully optimized for Vercel deployment.

## Prerequisites
1. A GitHub account.
2. A Vercel account.

## Deploying to Vercel
1. Push this `website` directory to your GitHub repository.
2. Log in to Vercel and click **Add New...** -> **Project**.
3. Import your `digital-wellbeing` repository.
4. **Important**: Since the website is located in a subdirectory, you must configure the **Root Directory** setting:
   - Edit the Root Directory to be `website`.
5. The Build Command (`npm run build`) and Output Directory (`.next`) will be automatically detected.
6. Click **Deploy**.

## Custom Domain Setup
To add a custom domain (e.g., `digitalwellbeing.app`):
1. In your Vercel project dashboard, go to **Settings** -> **Domains**.
2. Enter your domain name and click **Add**.
3. Follow the Vercel instructions to add the required `A` or `CNAME` records to your DNS provider. Vercel will automatically provision SSL certificates.

## Future Updates
Any time you push changes to the `main` branch (e.g., bumping `LATEST_VERSION` in `src/config/site.ts`), Vercel will automatically build and deploy the update in minutes.
