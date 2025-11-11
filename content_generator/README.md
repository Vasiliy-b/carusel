# Multi-Agent Content Generator

A sophisticated multi-agent system built with Google's Agent Development Kit (ADK) that processes viral Instagram posts and generates engaging carousel content.

## Architecture

```
Root Coordinator (Sequential)
├── 1. Data Collection Agent (gemini-2.5-flash)
├── 2. Content Analysis Pipeline (Sequential)
│   ├── Content Analyzer Agent (gemini-2.5-flash)
│   └── Creative Director Agent (gemini-2.5-flash) ← SUPERVISOR
├── 3. Content Generation Pipeline (Sequential)
│   ├── Copywriter Agent (gemini-2.5-flash)
│   └── Image Prompt Engineer Agent (gemini-2.5-flash)
├── 4. Image Generation (Parallel)
│   └── 10x Image Generator Agents (gemini-2.5-flash-image) ← NANOBABANA
└── 5. Results Manager Agent (gemini-2.5-flash)
```

## Features

- **Intelligent Filtering**: Automatically selects viral posts based on VIRALITY and ENGAGEMENT metrics
- **Creative Direction**: AI supervisor decides narrative vs independent carousel styles
- **Parallel Processing**: Generates 10 carousel images simultaneously
- **Cloud Storage**: Uploads to Google Cloud Storage with public URLs
- **Sheet Integration**: Updates Google Sheets with generated content metadata

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
# Edit .env with your actual values
```

**Required Variables:**
- `GOOGLE_CLOUD_PROJECT`: Your GCP project ID
- `GOOGLE_CLOUD_LOCATION`: GCP region (e.g., us-central1)
- `GCS_BUCKET`: Cloud Storage bucket name
- `GOOGLE_SHEETS_ID`: Already configured (10sNSObpUUfxtPs04owXeZjMm-dr-Z3Xh-UYXnepG5MM)

**Authentication (choose one):**

Option A: Vertex AI with ADC
```bash
gcloud auth application-default login
export GOOGLE_GENAI_USE_VERTEXAI=TRUE
```

Option B: Google AI Studio
```bash
export GOOGLE_API_KEY="your-api-key"
export GOOGLE_GENAI_USE_VERTEXAI=FALSE
```

### 3. Verify Setup

```bash
python -m content_generator.verify_setup
```

This checks:
- All environment variables
- Authentication credentials
- GCS bucket access
- Google Sheets accessibility
- Python dependencies
- Model configuration

## Usage

### Option 1: Run with ADK Web UI

```bash
# From project root
adk web
```

Then open http://localhost:8000 and select the `content_generator` agent.

### Option 2: Run Directly

```bash
python -m content_generator.main
```

### Option 3: Run with ADK CLI

```bash
adk run content_generator
```

## Workflow

1. **Data Collection**: Fetches posts from Google Sheets filtered by VIRALITY and ENGAGEMENT
2. **Content Analysis**: Analyzes each post's theme, hooks, narrative elements
3. **Creative Direction**: AI supervisor decides carousel style (narrative vs independent)
4. **Copy Generation**: Creates engaging headers and post captions
5. **Prompt Engineering**: Engineers 10 detailed prompts for gemini-2.5-flash-image
6. **Image Generation**: Generates 10 carousel images in parallel
7. **Results Management**: Uploads to GCS and updates sheet with metadata

## Models Used

- **gemini-2.5-flash**: Analysis, creative direction, copywriting, prompt engineering
- **gemini-2.5-flash-image** (nanobabana): Image generation with text overlay

## Output

Generated content is saved to:
- **Images**: Google Cloud Storage at `gs://{bucket}/posts/{post_id}/image_*.png`
- **Metadata**: Google Sheets (new tab or columns) with headers, captions, and URLs

## Configuration

Edit `.env` to customize:

### Filtering
```bash
VIRALITY_FILTER=VIRUS,BEST,GOOD
ENGAGEMENT_FILTER=BEST ER,VIRAL ER
```

### Generation
```bash
CAROUSEL_IMAGE_COUNT=10
IMAGE_FORMAT=PNG
MAX_PARALLEL_IMAGES=10
```

### Output
```bash
OUTPUT_MODE=new_tab           # or: new_columns, separate_sheet
OUTPUT_SHEET_NAME=Generated_Content
```

## Troubleshooting

### Authentication Issues

```bash
# Verify GCP authentication
gcloud auth list
gcloud config get-value project

# Re-authenticate if needed
gcloud auth application-default login
```

### Sheets Access

Make sure the sheet is public or you have the appropriate credentials configured.

### GCS Bucket

```bash
# Create bucket if it doesn't exist
gsutil mb -p YOUR_PROJECT_ID -l us-central1 gs://your-bucket-name

# Make bucket public (if desired)
gsutil iam ch allUsers:objectViewer gs://your-bucket-name
```

### Dependencies

```bash
# Reinstall all dependencies
pip install -r requirements.txt --upgrade
```

## Logging

Logs are saved to `logs/content_generator.log` by default.

Adjust log level in `.env`:
```bash
LOG_LEVEL=DEBUG  # or INFO, WARNING, ERROR
```

## Advanced Configuration

See `.env.example` for all available configuration options including:
- Retry attempts and delays
- Image quality settings
- State persistence
- Cost tracking
- Custom session IDs

## Support

For ADK documentation: https://google.github.io/adk-docs/

## License

Built with Google Agent Development Kit (ADK)

