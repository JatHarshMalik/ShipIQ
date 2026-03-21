# ShipIQ Frontend

Modern React frontend for the Cargo Optimization System built with Vite.

## Features

- 🎨 Beautiful, responsive UI with modern design
- 📊 Real-time cargo allocation visualization
- 📈 Interactive statistics and progress bars
- 🚀 Fast performance with Vite
- 🎯 Intuitive cargo and tank management

## Quick Start

### Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The application will be available at http://localhost:3000

### Production Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

### Docker

```bash
docker build -t shipiq-frontend .
docker run -p 80:80 shipiq-frontend
```

## Environment Variables

Create a `.env` file based on `.env.example`:

- `VITE_API_URL`: Backend API URL (default: http://localhost:8000)

## Tech Stack

- React 18
- Vite 5
- Axios for API calls
- Lucide React for icons
- CSS3 with modern features
