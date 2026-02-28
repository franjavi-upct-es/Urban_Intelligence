# Urban Intelligence Framework - Frontend

# React + TypeScript dashboard for price prediction

# Urban Intelligence Frontend

A modern React + TypeScript dashboard for the Urban Intelligence price prediction platform.

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **TailwindCSS** - Styling
- **React Query** - Server state management
- **React Router** - Navigation
- **Recharts** - Data visualization
- **Lucide React** - Icons

## Features

- 📊 **Dashboard** - Overview of system status and metrics
- 💰 **Price Prediction** - Interactive prediction form
- 🌍 **Cities** - Data management and statistics
- 📈 **Analytics** - Deep dive into pricing patterns
- 🧪 **A/B Testing** - Model experimentation
- 📡 **Monitoring** - Real-time performance tracking
- ⚙️ **Settings** - System configuration

## Getting Started

### Prerequisites

- Node.js 18+
- npm or pnpm

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Environment Variables

Copy `.env.example` to `.env` and configure:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
```

## Project Structure

```
frontend/
├── public/              # Static assets
├── src/
│   ├── components/      # Reusable components
│   │   ├── ui/          # Base UI components
│   │   ├── charts/      # Chart components
│   │   └── Layout.tsx   # Main layout
│   ├── hooks/           # Custom React hooks
│   ├── pages/           # Page components
│   ├── services/        # API services
│   ├── types/           # TypeScript types
│   ├── utils/           # Utility functions
│   ├── App.tsx          # Root component
│   ├── main.tsx         # Entry point
│   └── index.css        # Global styles
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── vite.config.ts
```

## Available Scripts

| Command              | Description                   |
| -------------------- | ----------------------------- |
| `npm run dev`        | Start development server      |
| `npm run build`      | Build for production          |
| `npm run preview`    | Preview production build      |
| `npm run lint`       | Run ESLint                    |
| `npm run type-check` | Run TypeScript compiler check |

## API Integration

The frontend connects to the FastAPI backend. Key API endpoints:

- `GET /health` - Health check
- `POST /predict` - Price prediction
- `GET /cities` - List cities
- `GET /cities/{id}/statistics` - City statistics
- `GET /monitoring/performance` - Performance metrics
- `GET /experiments` - A/B experiments
- `WS /ws` - WebSocket for real-time updates

## Styling

Uses TailwindCSS with a custom color palette:

- **Primary**: Sky blue (`#0ea5e9`)
- **Accent**: Fuchsia (`#d946ef`)
- **Success**: Green
- **Warning**: Amber
- **Error**: Red

Dark mode is supported via the `dark:` prefix.

## Contributing

1. Create a feature branch
2. Make changes
3. Run `npm run lint` and `npm run type-check`
4. Submit a pull request

## License

MIT License
