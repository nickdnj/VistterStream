import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../../services/api';
import SlideOver from '../shared/SlideOver';
import PositionPicker from '../shared/PositionPicker';

interface ExportDialogProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: number | null;
  pngDataUrl: string | null;
}

const ExportDialog: React.FC<ExportDialogProps> = ({ isOpen, onClose, projectId, pngDataUrl }) => {
  const [assetName, setAssetName] = useState('');
  const [positionX, setPositionX] = useState(0.0);
  const [positionY, setPositionY] = useState(0.0);
  const [opacity, setOpacity] = useState(1.0);
  const [exporting, setExporting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [exportedAssetId, setExportedAssetId] = useState<number | null>(null);
  const navigate = useNavigate();

  const handleExportAsAsset = async () => {
    if (!projectId || !pngDataUrl || !assetName.trim()) return;
    setExporting(true);
    try {
      const resp = await api.post(`/canvas-projects/${projectId}/export`, {
        asset_name: assetName.trim(),
        png_data: pngDataUrl,
        position_x: positionX,
        position_y: positionY,
        opacity,
      });
      setExportedAssetId(resp.data.id);
      setSuccess(true);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Export failed');
    } finally {
      setExporting(false);
    }
  };

  const handleDownloadPng = () => {
    if (!pngDataUrl) return;
    const link = document.createElement('a');
    link.download = `${assetName || 'canvas-export'}.png`;
    link.href = pngDataUrl;
    link.click();
  };

  const handleClose = () => {
    setSuccess(false);
    setExportedAssetId(null);
    setAssetName('');
    setPositionX(0);
    setPositionY(0);
    setOpacity(1);
    onClose();
  };

  return (
    <SlideOver
      isOpen={isOpen}
      onClose={handleClose}
      title="Export Canvas"
      subtitle="Create an overlay asset from your design"
      footer={
        success ? (
          <div className="flex gap-3">
            <button
              onClick={() => navigate('/assets')}
              className="flex-1 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-medium transition-colors"
            >
              View in Assets
            </button>
            <button
              onClick={handleClose}
              className="px-4 py-2 bg-dark-700 hover:bg-dark-600 text-gray-300 rounded-lg text-sm transition-colors"
            >
              Close
            </button>
          </div>
        ) : (
          <div className="flex gap-3">
            <button
              onClick={handleClose}
              className="px-4 py-2 bg-dark-700 hover:bg-dark-600 text-gray-300 rounded-lg text-sm transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleDownloadPng}
              disabled={!pngDataUrl}
              className="px-4 py-2 bg-dark-600 hover:bg-dark-500 text-white rounded-lg text-sm transition-colors disabled:opacity-40"
            >
              Download PNG
            </button>
            <button
              onClick={handleExportAsAsset}
              disabled={exporting || !assetName.trim() || !pngDataUrl}
              className="flex-1 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
            >
              {exporting ? 'Exporting...' : 'Export as Asset'}
            </button>
          </div>
        )
      }
    >
      {success ? (
        <div className="text-center py-8">
          <div className="w-16 h-16 bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-green-400 text-3xl">&#10003;</span>
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">Asset Created!</h3>
          <p className="text-gray-400 text-sm">
            Your canvas has been exported as asset #{exportedAssetId}
          </p>
        </div>
      ) : (
        <div className="space-y-5">
          {/* Preview */}
          {pngDataUrl && (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Preview</label>
              <div className="bg-dark-900 border border-dark-700 rounded-lg overflow-hidden">
                <img src={pngDataUrl} alt="Canvas preview" className="w-full object-contain max-h-48" />
              </div>
            </div>
          )}

          {/* Asset name */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Asset Name</label>
            <input
              type="text"
              value={assetName}
              onChange={(e) => setAssetName(e.target.value)}
              placeholder="My Canvas Overlay"
              className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-md text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          {/* Position picker */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Position</label>
            <PositionPicker
              positionX={positionX}
              positionY={positionY}
              onChange={(x, y) => { setPositionX(x); setPositionY(y); }}
              showRawInputs
            />
          </div>

          {/* Opacity */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Opacity: {Math.round(opacity * 100)}%
            </label>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={opacity}
              onChange={(e) => setOpacity(parseFloat(e.target.value))}
              className="w-full accent-primary-500"
            />
          </div>
        </div>
      )}
    </SlideOver>
  );
};

export default ExportDialog;
