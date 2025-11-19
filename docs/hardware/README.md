# Hardware Documentation & Images

This folder contains hardware documentation and reference images for VistterStream.

## Documentation

- **[HARDWARE_GUIDE.md](HARDWARE_GUIDE.md)** - Complete hardware guide with specifications, setup, and troubleshooting

## Images Needed

To complete the hardware documentation, add the following images to this folder:

### Required Images

1. **hardware-setup.jpg** - Overall system photo showing all components together
   - Raspberry Pi 5 with case
   - Cameras (Sunba PTZ, Reolink)
   - Tempest weather station
   - Network switch
   - Suggested: Professional product photo style

2. **raspberry-pi-5.jpg** - Close-up of Raspberry Pi 5
   - Show the Pi in its case with cooling
   - Connected cables visible (Ethernet, power)
   - Suggested: Clear, well-lit photo from 45° angle

3. **sunba-ptz-camera.jpg** - Sunba PTZ camera
   - Mounted position showing camera
   - Highlight PTZ movement capability
   - Suggested: Outdoor installation photo

4. **reolink-camera.jpg** - Reolink fixed camera (optional)
   - Show camera mounting
   - Demonstrate typical installation
   - Suggested: Wide shot showing coverage area

5. **tempest-weather-station.jpg** - Tempest weather station
   - Show station mounted on pole
   - Clear view of sensors
   - Suggested: Outdoor location with clear sky visible

6. **weather-overlay-example.jpg** - Screenshot of stream with weather overlay
   - Capture from VistterStream showing:
     - Camera feed
     - Weather data overlay
     - Professional appearance
   - Suggested: Take screenshot during interesting weather

### Optional Enhancement Images

7. **network-diagram-photo.jpg** - Physical network setup
   - Show switch with connected cables
   - Labeled cables (Pi, cameras, network)
   - Cable management example

8. **ptz-presets-demo.jpg** - Multiple angles from PTZ camera
   - Side-by-side comparison of 3-4 preset positions
   - Demonstrate multi-angle capability
   - Show VistterStream preset UI

9. **power-setup.jpg** - Power distribution setup
   - UPS if equipped
   - PoE switch or power supplies
   - Clean power management

10. **cooling-setup.jpg** - Raspberry Pi cooling solution
    - Active cooler on Pi 5
    - Temperature monitoring screenshot
    - Show thermal performance

## Image Guidelines

**Format:**
- Format: JPG or PNG
- Resolution: Minimum 1920x1080 for main photos
- File size: Keep under 5MB per image
- Compression: Balance quality and file size

**Content:**
- Clear, well-lit photos
- Focus on the hardware
- Show relevant details and connections
- Professional presentation
- Include scale reference when helpful

**Naming:**
- Use exact filenames listed above
- Lowercase with hyphens
- Descriptive but concise

**Editing:**
- Crop to remove distractions
- Adjust exposure/contrast for clarity
- Add labels/arrows if helpful (use image editor)
- Maintain realistic colors

## Taking Good Hardware Photos

### Equipment
- Use a decent camera (smartphone is fine)
- Natural lighting preferred
- Clean background (neutral color)
- Tripod or stable surface

### Composition
- Rule of thirds for main subject
- Show context (where/how it's used)
- Multiple angles if complex
- Close-ups for details

### Preparation
- Clean all hardware before photographing
- Organize cables neatly
- Remove clutter from background
- Ensure LEDs/displays are visible

## Screenshot Examples

For weather overlay example:
1. Start a stream with weather overlay in VistterStream
2. Open the stream in browser
3. Take screenshot during interesting conditions
4. Crop to show just the video frame
5. Annotate to highlight weather data

## Adding Images to Documentation

Once you have images, they're already referenced in `HARDWARE_GUIDE.md`:

```markdown
![Raspberry Pi 5](raspberry-pi-5.jpg)
```

Just place the images in this folder and the guide will display them automatically.

## Alternative: Use Product Photos

If taking your own photos isn't feasible:

1. **Raspberry Pi 5**: Use official product photos from raspberrypi.com
2. **Cameras**: Use manufacturer product photos
3. **Tempest**: Use WeatherFlow product photos

**Important**: Ensure you have rights to use any images. Product photos from manufacturers are usually fine for documentation like this, but check their media/press pages for official images.

## Diagram Images

Some sections reference diagrams:
- Network topology diagram (can be created with draw.io or similar)
- Power consumption chart (can be screenshot from spreadsheet)
- Performance graphs (can be captured from monitoring tools)

---

**Have images?** Place them in this folder and they'll automatically appear in the [HARDWARE_GUIDE.md](HARDWARE_GUIDE.md)!

