/**
 * Resolve an asset's display image URL based on its type.
 * API images use the backend proxy to avoid HTTPS mixed-content issues.
 */
export function getAssetImageUrl(asset: { id?: number; type: string; file_path: string | null; api_url: string | null }): string | null {
  if (asset.type === 'api_image') {
    // Use backend proxy to avoid mixed-content when accessed via HTTPS tunnel
    if (asset.id) return `/api/assets/${asset.id}/proxy`;
    if (asset.api_url) return asset.api_url;
  }
  if (asset.type === 'static_image' && asset.file_path) return asset.file_path;
  if (asset.type === 'google_drawing' && asset.file_path) {
    const match = asset.file_path.match(/\/drawings\/d\/([a-zA-Z0-9_-]+)/);
    return match ? `https://docs.google.com/drawings/d/${match[1]}/export/png` : null;
  }
  return null;
}
