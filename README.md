# VistterStream Appliance

VistterStream is the local streaming appliance that connects on-premises cameras to VistterStudio cloud timelines. Running on hardware like the Raspberry Pi in a Docker container, VistterStream discovers, manages, and processes local cameras, including PTZ (pan-tilt-zoom) presets. It ingests RTSP/RTMP feeds, applies overlays and instructions received from VistterStudio, and streams the final output to destinations such as YouTube Live, Facebook Live, or Twitch.

## Features

*   **Camera & PTZ Management:** Discover, manage, and control local RTSP/RTMP cameras, including PTZ presets.
*   **Web Interface:** A local web UI for camera configuration, live previews, and system monitoring.
*   **Streaming & Processing:** Uses FFmpeg to ingest, transcode, and apply overlays to camera feeds.
*   **Multi-Output:** Stream to multiple services like YouTube Live, Facebook Live, and Twitch simultaneously.
*   **Cloud Integration:** Seamlessly integrates with VistterStudio for timeline execution and overlay synchronization.
*   **Dockerized:** Runs in a Docker container on Raspberry Pi or any other Docker-compatible device.

## Getting Started

To get started with VistterStream, you'll need to have Docker and Docker Compose installed on your system.

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/nickdnj/VistterStream.git
    cd VistterStream
    ```

2.  **Build and run the application:**

    ```bash
    docker-compose up --build
    ```

    This will build the Docker images and start the backend and frontend services.

3.  **Access the application:**

    *   **Backend API:** `http://localhost:8000`
    *   **Frontend Web UI:** `http://localhost:3000`

## Technology Stack

*   **Backend:** FastAPI (Python)
*   **Frontend:** React
*   **Database:** SQLite
*   **Streaming Engine:** FFmpeg
*   **Containerization:** Docker

## Project Structure

```
.
├── backend/
│   ├── controllers.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   └── requirements.txt
├── docker/
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
├── docker-compose.yml
├── docs/
│   ├── PRD.md
│   ├── SAD.md
│   └── UXD.md
├── frontend/
│   ├── package.json
│   └── src/
├── stream-engine/
│   └── main.py
└── tests/
    └── test_backend.py
```

## API Endpoints

*   `/auth`: Authentication and user management.
*   `/cameras`: CRUD operations for cameras.
*   `/presets`: CRUD operations for PTZ presets.
*   `/streams`: Start, stop, and monitor streams.
*   `/status`: System health and metrics.
*   `/overlays`: Synchronize overlays from VistterStudio.

## Contributing

Contributions are welcome! Please feel free to submit a pull request.

## License

This project is licensed under the MIT License.