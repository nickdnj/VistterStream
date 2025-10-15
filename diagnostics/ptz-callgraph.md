# PTZ Call Graph (Vistter Stream)

```mermaid
flowchart TD
    subgraph API Layer
        A[POST /api/presets/{id}/move]
        B[POST /api/presets/capture]
    end

    subgraph Services
        C[PTZService.move_to_preset]
        D[PTZService.get_current_position]
        E[PTZService.set_preset]
        F[PTZService.get_onvif_camera]
    end

    subgraph External
        G[ONVIFCamera.create_ptz_service()]
        H[ONVIFCamera.create_media_service()]
        I[PTZ Service: GotoPreset]
        J[PTZ Service: GetStatus]
        K[PTZ Service: SetPreset]
        L[Media Service: GetProfiles]
    end

    A -->|Fetch preset + camera| C
    C --> F
    F --> G
    F --> H
    G --> H
    H --> L
    C -->|Create request| I
    I -->|Camera executes preset| Camera((Sunba PTZ))

    B -->|Fetch camera| D
    B -->|Persist Preset row| DB[(Database)]
    D --> F
    D --> G
    D --> H
    D --> J
    B -->|After persist| E
    E --> F
    E --> G
    E --> H
    E --> K
    E -->|Update preset token| DB

    subgraph Automation
        T[TimelineExecutor]
        U[StreamService.start_stream]
    end

    T -->|Segment requires preset| C
    U -->|Stream uses preset| C
```

- **Notes**
- `PTZService.get_onvif_camera` caches camera handles per `address:port` and probes fallback ports `8899`, `8000`, `80`.
- All service methods rely on `asyncio.get_event_loop().run_in_executor` to call blocking zeep SOAP stubs.
- Credential material is retrieved in the routers/services and passed into PTZService; passwords are base64-decoded inside router functions.
- `capture_current_position` seeds `camera_preset_token` with the preset id before calling `SetPreset`, covering cameras that do not return a token.
```
