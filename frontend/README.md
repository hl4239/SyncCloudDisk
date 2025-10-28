# Task Management System

A modern task management dashboard built with Next.js, featuring workflow automation and real-time monitoring.

## Features

- **Task Management**: Create, monitor, and manage tasks with real-time status updates
- **Workflow Management**: Browse and configure available workflows with parameter schemas
- **Scheduler**: Create and manage scheduled jobs with cron expressions
- **Theme Support**: Light/dark mode with system preference detection
- **Responsive Design**: Mobile-first design with modern UI components

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn
- Your API server running (see API Configuration below)

### Installation

1. Clone or download the project
2. Install dependencies:

\`\`\`bash
npm install
# or
yarn install
\`\`\`

3. Set up environment variables (see Environment Variables section)

4. Run the development server:

\`\`\`bash
npm run dev
# or
yarn dev
\`\`\`

5. Open [http://localhost:3000](http://localhost:3000) in your browser

### Environment Variables

Create a `.env.local` file in the root directory:

\`\`\`env
# API Configuration
NEXT_PUBLIC_API_BASE=http://localhost:8000/api/v1
\`\`\`

Replace `http://localhost:8000/api/v1` with your actual API server URL.

### API Configuration

This frontend expects a REST API with the following endpoints:

- `GET /tasks` - List all tasks
- `POST /tasks` - Create a new task
- `GET /tasks/{task_id}` - Get task details
- `GET /workflows` - List available workflows
- `GET /workflows/{workflow_name}` - Get workflow details
- `POST /scheduler/jobs` - Create scheduled job
- `GET /scheduler/jobs` - List scheduled jobs
- `PUT /scheduler/jobs/{job_id}` - Update scheduled job
- `DELETE /scheduler/jobs/{job_id}` - Delete scheduled job

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript type checking

## Project Structure

\`\`\`
├── app/                    # Next.js app directory
│   ├── layout.tsx         # Root layout with theme provider
│   ├── page.tsx           # Main dashboard page
│   └── globals.css        # Global styles and theme variables
├── components/            # React components
│   ├── ui/               # shadcn/ui components
│   ├── task-dashboard.tsx # Task management interface
│   ├── workflow-manager.tsx # Workflow browsing interface
│   ├── scheduler-manager.tsx # Job scheduling interface
│   └── theme-toggle.tsx  # Theme switching component
├── lib/                  # Utility functions
│   └── api.ts           # API client functions
└── types/               # TypeScript type definitions
    └── api.ts          # API response types
\`\`\`

## Deployment

### Vercel (Recommended)

1. Push your code to GitHub
2. Connect your repository to Vercel
3. Set the `NEXT_PUBLIC_API_BASE` environment variable in Vercel dashboard
4. Deploy

### Other Platforms

1. Build the project: `npm run build`
2. Start the production server: `npm start`
3. Ensure environment variables are properly configured

## Troubleshooting

### API Connection Issues

- Verify your API server is running and accessible
- Check the `NEXT_PUBLIC_API_BASE` environment variable
- Ensure CORS is properly configured on your API server
- Check browser console for network errors

### Theme Issues

- Clear browser cache and localStorage
- Check if system theme preference is being detected correctly
- Verify theme provider is properly wrapped around the app

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request
