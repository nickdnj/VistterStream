# Manual Installation - Preview System

**Quick manual setup since sudo password is needed**

## Step 1: Install MediaMTX (needs sudo password)

```bash
# Extract MediaMTX (already downloaded to /tmp)
cd /tmp
tar -xzf mediamtx.tar.gz

# Install to /usr/local/bin (ENTER YOUR PASSWORD when prompted)
sudo mv mediamtx /usr/local/bin/
sudo chmod +x /usr/local/bin/mediamtx

# Create config directory
sudo mkdir -p /etc/vistterstream
sudo cp /Users/nickd/Workspaces/VistterStream/docker/mediamtx/mediamtx.yml /etc/vistterstream/
```

## Step 2: Verify MediaMTX

```bash
mediamtx --version
```

Should show version 1.15.1

## Step 3: Backend Dependencies (already done by installer)

```bash
cd /Users/nickd/Workspaces/VistterStream
source venv/bin/activate
pip install httpx
```

## Step 4: Frontend Dependencies (ALREADY DONE ✅)

```bash
cd /Users/nickd/Workspaces/VistterStream/frontend
npm install  # Already ran, hls.js installed
```

## Step 5: Start Everything

**Terminal 1 - MediaMTX:**
```bash
mediamtx /etc/vistterstream/mediamtx.yml
```

**Terminal 2 - Backend:**
```bash
cd /Users/nickd/Workspaces/VistterStream/backend
source ../venv/bin/activate
python start.py
```

**Terminal 3 - Frontend:**
```bash
cd /Users/nickd/Workspaces/VistterStream/frontend
npm start
```

## Step 6: Test Preview

1. Open http://localhost:3000
2. Go to Timeline Editor
3. Select a timeline
4. Click "Start Preview"
5. Video should appear!

---

**STATUS**: Backend fixed ✅, Frontend fixed ✅, Dependencies installed ✅
**NEXT**: Install MediaMTX with sudo, then start testing!

