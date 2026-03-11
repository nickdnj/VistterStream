/**
 * Resolve an asset's display image URL based on its type.
 */
export function getAssetImageUrl(asset: { type: string; file_path: string | null; api_url: string | null }): string | null {
  if (asset.type === 'api_image' && asset.api_url) return asset.api_url;
  if (asset.type === 'static_image' && asset.file_path) return asset.file_path;
  if (asset.type === 'google_drawing' && asset.file_path) {
    const match = asset.file_path.match(/\/drawings\/d\/([a-zA-Z0-9_-]+)/);
    return match ? `https://docs.google.com/drawings/d/${match[1]}/export/png` : null;
  }
  return null;
}
