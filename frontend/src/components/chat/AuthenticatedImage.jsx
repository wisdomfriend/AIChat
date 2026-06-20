/**
 * 带 Bearer 认证的图片预览。
 */
import { useEffect, useState } from "react";
import { fetchImageBlobUrl } from "../../services/chatApi";

export default function AuthenticatedImage({ fileId, alt }) {
  const [src, setSrc] = useState("");

  useEffect(() => {
    let cancelled = false;
    let objectUrl = "";

    async function load() {
      try {
        objectUrl = await fetchImageBlobUrl(fileId);
        if (!cancelled) {
          setSrc(objectUrl);
        }
      } catch {
        if (!cancelled) {
          setSrc("");
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [fileId]);

  if (!src) {
    return <div className="image-placeholder">图片加载中...</div>;
  }

  return <img src={src} alt={alt || "upload"} className="message-image" />;
}
