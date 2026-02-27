# LLM Judge: AI vs Human

## Overview
This is a multimodal evaluation demo application designed to run in a containerized environment using Docker. It uses a Google AI Studio API key to access the Gemini 2.5 Flash model for analyzing both text and video inputs. Inputs are processed through a feed-forward LLM call. API usage is rate-limited according to thresholds defined in `models_config.json`, and request records are stored persistently to enforce limits across sessions.

## Getting Started

### Prerequisites
- Docker and Docker Compose
- A Google Gemini API Key

### Running the Application
1. Clone the repository and navigate to the project directory.
2. Build and start the container in detached mode:
   ```bash
   docker-compose up -d --build
   ```
3. Access the application UI at http://localhost:8501.
4. Enter your Gemini API Key directly into the application dashboard to begin analysis.

### Managing the Container
- **View Logs**: `docker-compose logs -f app`
- **Stop Application**: `docker-compose down`

## Assumptions
- **Single Deployment Container**: No scaling beyond a single deployment instance.
- **Input Limits**: 1000-word limit for text and a 20MB limit for video.

## Future Improvements
- **Micro-services Architecture**: Introduce evaluation and tracing services.
- **Fine-grained Analysis**: Implement timestamp-specific markers in video analysis to point out exactly where crucial signals are detected.
- **Asynchronous Workflows**: Move video processing to a background task queue to handle larger files without blocking the user interface.
- **Batch Processing**: Add the ability to upload multiple files or a URL list for high-volume content auditing.
- **Introduce Agentic Flows**: Break down video feeds into frames and analyze the footage with timestamps. To build a detailed analysis of crucial points, these frames can be cross-referenced against domain-specific models (e.g., gesture analysis or physics engines).
- **External Validation**: Use internet search APIs to determine if similar content already exists online and verify its current standing.
