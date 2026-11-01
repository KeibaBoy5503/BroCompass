// 휴대폰 사진(수 MB)을 분석용으로 줄인다. 업로드 시간·무료 API의 입력 크기 제한을 함께 고려한 값이다.
// 음식 인식에는 긴 변 768px 정도면 충분하다.

const SCALES = [1, 0.75, 0.56];
const QUALITIES = [0.8, 0.68, 0.56];
const MAX_EDGE = 768;
const TARGET_BYTES = 150 * 1024;

export type CompressedImage = { base64: string; mime: "image/jpeg"; bytes: number };

function toBlob(canvas: HTMLCanvasElement, quality: number): Promise<Blob> {
  return new Promise((resolve, reject) =>
    canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("이미지 변환에 실패했어요."))), "image/jpeg", quality)
  );
}

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const s = String(reader.result);
      resolve(s.slice(s.indexOf(",") + 1)); // data:...;base64, 접두사 제거
    };
    reader.onerror = () => reject(new Error("이미지를 읽지 못했어요."));
    reader.readAsDataURL(blob);
  });
}

export async function compressImage(file: File): Promise<CompressedImage> {
  if (!file.type.startsWith("image/")) throw new Error("이미지 파일만 선택할 수 있어요.");

  let bitmap: ImageBitmap;
  try {
    // from-image: 폰으로 찍은 사진의 EXIF 회전을 반영해 옆으로 누운 사진이 되지 않게 한다.
    bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
  } catch {
    throw new Error("이 이미지를 열 수 없어요. JPEG 또는 PNG 사진을 사용해 주세요.");
  }

  try {
    const base = Math.min(1, MAX_EDGE / Math.max(bitmap.width, bitmap.height));
    let last: Blob | null = null;
    // 목표 크기 이하가 될 때까지 해상도 → 화질 순으로 낮춘다. 끝까지 크면 가장 작은 결과를 쓴다.
    for (const s of SCALES) {
      const w = Math.max(1, Math.round(bitmap.width * base * s));
      const h = Math.max(1, Math.round(bitmap.height * base * s));
      const canvas = document.createElement("canvas");
      canvas.width = w;
      canvas.height = h;
      const ctx = canvas.getContext("2d");
      if (!ctx) throw new Error("이미지를 처리할 수 없는 브라우저예요.");
      ctx.fillStyle = "#fff"; // 투명 PNG 가 검게 변하지 않도록
      ctx.fillRect(0, 0, w, h);
      ctx.drawImage(bitmap, 0, 0, w, h);
      for (const q of QUALITIES) {
        last = await toBlob(canvas, q);
        if (last.size <= TARGET_BYTES) return { base64: await blobToBase64(last), mime: "image/jpeg", bytes: last.size };
      }
    }
    if (!last) throw new Error("이미지 변환에 실패했어요.");
    return { base64: await blobToBase64(last), mime: "image/jpeg", bytes: last.size };
  } finally {
    bitmap.close();
  }
}
