# Multi-Agent Content Generator

AI-powered Instagram carousel content generator using Google ADK multi-agent system.

## Features

- Fetches posts from Google Sheets
- Randomly selects 1 post for processing
- Multi-agent pipeline: Analysis → Creative Direction → Copywriting → Image Prompts → Image Generation
- Generates 10 carousel images with 3D plasticine style
- Web UI for SMM team to trigger and browse generations
- RunPod deployment ready

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Google Cloud Project with Vertex AI enabled
- Google Sheets with content data
- Service account JSON credentials

### 2. Installation

```bash
git clone https://github.com/YOUR_USERNAME/ADK.git
cd ADK

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r web_ui/requirements.txt
```

### 3. Configuration

```bash
# Copy example config
cp .env.example content_generator/.env

# Edit with your values
nano content_generator/.env
```

Required settings:
- `GOOGLE_CLOUD_PROJECT` - Your GCP project ID
- `GOOGLE_SHEETS_ID` - Your Google Sheet ID
- Place service account JSON in project root

### 4. Run Web UI

```bash
export STYLE="pastel colors, soft lighting, elegant, clean style, 3d render, high detail, 3d plasticine"
python -m flask --app web_ui.app run --host=0.0.0.0 --port=5000
```

Or use the convenience script:
```bash
chmod +x start_web_ui.sh
./start_web_ui.sh
```

Access: http://localhost:5000

## Architecture

### Multi-Agent System

1. **DataCollector** - Fetches posts from Google Sheets
2. **PostSelector** - Picks 1 random post
3. **ContentAnalyzer** - Analyzes topic, tone, style
4. **CreativeDirector** - Defines art style, colors, layout
5. **Copywriter** - Creates title, caption, hashtags, slide texts
6. **ImagePromptEngineer** - Creates 10 detailed prompts
7. **PromptFormatter** - Auto-fixes prompts (art style, natural colors)
8. **ImageGenerator** (Loop) - Generates 10 images
9. **ResultsManager** - Saves metadata as .md file
10. **StateCleaner** - Prepares for next run

### Output Structure

```
output/posts/post_[id]_[timestamp]/
├── images/
│   ├── slide_01_Text.png
│   ├── slide_02_Text.png
│   └── ... (10 total)
└── post_[id]_[timestamp]_content.md
```

## Web UI

Simple Flask interface with:
- **Gallery View**: Browse all generated posts
- **Generate Button**: Trigger new random post generation
- **Post Detail**: View carousel + metadata
- **Persistent Status**: Loader survives page refresh

## RunPod Deployment

### Build & Push Docker Image

```bash
# Build
docker build -t YOUR_USERNAME/content-generator:latest .

# Push to Docker Hub
docker login
docker push YOUR_USERNAME/content-generator:latest
```

### Create RunPod Instance

1. Go to RunPod.io
2. Create Pod with:
   - Image: `YOUR_USERNAME/content-generator:latest`
   - Expose port: 5000 → HTTP
   - Volume: `/app/output` (persistent storage)

3. Environment variables:
```
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=TRUE
STYLE=pastel colors, soft lighting, elegant, clean style, 3d render, high detail, 3d plasticine
```

4. Mount service account credentials:
   - Upload JSON to volume
   - Set `GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json`

5. Access via RunPod's public URL

## Cost Safety

**Idle state: $0.00** - No background processes

**Per generation: ~$0.05-$0.10**
- Gemini 2.5 Flash (text): ~$0.0003
- Gemini 2.5 Flash Image (10 images): ~$0.05-$0.10

Manual trigger only - no automatic generation.

## Development

### Run CLI Generator (No UI)

```bash
python -m content_generator.main
```

### Test Setup

```bash
python -m content_generator.verify_setup
```

### View Logs

```bash
tail -f logs/content_generator.log
```

## Project Structure

```
ADK/
├── content_generator/          # Multi-agent system
│   ├── agents.py              # Agent definitions
│   ├── orchestrator.py        # Agent orchestration
│   ├── tools.py               # Custom tools
│   ├── config.py              # Configuration
│   ├── main.py                # CLI entry point
│   └── ...
├── web_ui/                     # Flask web interface
│   ├── app.py                 # Flask server
│   ├── templates/             # HTML templates
│   ├── static/                # CSS, JS
│   └── requirements.txt
├── docs/                       # ADK documentation
├── Dockerfile                  # Container setup
├── requirements.txt            # Python dependencies
└── start_web_ui.sh            # Quick start script
```

## License

MIT

## Credits

Built with [Google ADK](https://github.com/google/adk) (Agent Development Kit)

