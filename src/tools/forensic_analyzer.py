"""
Forensic Analyzer: Görsele forensic önişleme uygular.
- ELA (Error Level Analysis): Sıkıştırma tutarsızlığı haritası
- FFT Magnitude: Frekans alanı analizi
- Edge Density: Kenar yoğunluğu haritası
- Edge Pattern Analysis: AI tespit için edge yapı analizi
"""

from pathlib import Path
from io import BytesIO
import numpy as np
from PIL import Image, ImageChops, ImageEnhance
import cv2


class ForensicAnalyzer:
    """Görsel için forensic önişleme."""

    def __init__(self, target_size: int = 512):
        self.target_size = target_size

    def _resize_image(self, image: Image.Image) -> Image.Image:
        ratio = self.target_size / max(image.size)
        if ratio < 1:
            new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
            image = image.resize(new_size, Image.LANCZOS)
        return image

    def compute_ela(self, image_path: Path, quality: int = 90) -> Image.Image:
        original = Image.open(image_path).convert("RGB")
        original = self._resize_image(original)

        buffer = BytesIO()
        original.save(buffer, format="JPEG", quality=quality)
        buffer.seek(0)
        recompressed = Image.open(buffer)

        ela = ImageChops.difference(original, recompressed)
        extrema = ela.getextrema()
        max_diff = max([ex[1] for ex in extrema])
        if max_diff == 0:
            max_diff = 1
        scale = 255.0 / max_diff
        ela = ImageEnhance.Brightness(ela).enhance(scale)
        return ela

    def compute_fft_magnitude(self, image_path: Path) -> Image.Image:
        original = Image.open(image_path).convert("L")
        original = self._resize_image(original)
        arr = np.array(original, dtype=np.float32)

        fft = np.fft.fft2(arr)
        fft_shifted = np.fft.fftshift(fft)
        magnitude = np.log(np.abs(fft_shifted) + 1)
        magnitude = (magnitude - magnitude.min()) / (magnitude.max() - magnitude.min())
        magnitude = (magnitude * 255).astype(np.uint8)

        return Image.fromarray(magnitude)

    def compute_edge_map(self, image_path: Path) -> np.ndarray:
        """Edge detection — numpy array döndürür (analiz için)."""
        original = Image.open(image_path).convert("L")
        original = self._resize_image(original)
        arr = np.array(original)
        edges = cv2.Canny(arr, threshold1=50, threshold2=150)
        return edges

    def analyze_edge_patterns(self, edges: np.ndarray) -> dict:
        """
        Edge map'inden AI tespit metrikleri çıkar.

        AI imzaları:
        - Düşük edge uniformity variance (her yer aynı yoğunlukta)
        - Yüksek texture repetition (tekrar eden pattern'ler)
        - Düşük density spread (uniform dağılım)
        """
        h, w = edges.shape

        # 1. EDGE UNIFORMITY (8x8 grid variance)
        grid_size = 8
        cell_h, cell_w = h // grid_size, w // grid_size
        cell_densities = []

        for i in range(grid_size):
            for j in range(grid_size):
                cell = edges[
                    i * cell_h:(i + 1) * cell_h,
                    j * cell_w:(j + 1) * cell_w
                ]
                density = (cell > 0).sum() / cell.size
                cell_densities.append(density)

        cell_densities = np.array(cell_densities)
        # Düşük std = uniform = AI işareti
        uniformity_std = float(cell_densities.std())
        uniformity_mean = float(cell_densities.mean())

        # 2. TEXTURE REPETITION (patch similarity)
        # Görseli 32x32 patch'lere böl, ortalama benzerlik
        patch_size = 32
        patches = []
        for i in range(0, h - patch_size, patch_size):
            for j in range(0, w - patch_size, patch_size):
                patch = edges[i:i + patch_size, j:j + patch_size]
                patches.append(patch.flatten())

        # En çok 50 patch'i karşılaştır (hız için)
        if len(patches) > 50:
            indices = np.linspace(0, len(patches) - 1, 50, dtype=int)
            patches = [patches[i] for i in indices]

        patches = np.array(patches, dtype=np.float32)

        # Pairwise correlation
        if len(patches) > 1:
            # Her patch'i normalize et
            norms = np.linalg.norm(patches, axis=1, keepdims=True)
            norms[norms == 0] = 1
            normalized = patches / norms
            # Cosine similarity matrix
            similarity = normalized @ normalized.T
            # Diagonal'ı çıkar (kendisiyle benzerliği)
            np.fill_diagonal(similarity, 0)
            avg_similarity = float(similarity.mean())
        else:
            avg_similarity = 0.0

        # 3. DENSITY DISTRIBUTION (histogram analizi)
        # Eğer dağılım uniform ise AI işareti, bimodal ise real
        hist, _ = np.histogram(cell_densities, bins=10)
        hist_normalized = hist / hist.sum() if hist.sum() > 0 else hist
        # Entropy: yüksek = uniform dağılım
        entropy = -np.sum([p * np.log(p + 1e-10) for p in hist_normalized])

        # 4. OVERALL EDGE DENSITY
        overall_density = float((edges > 0).sum() / edges.size)

        return {
            "edge_density": overall_density,
            "uniformity_std": uniformity_std,
            "uniformity_mean": uniformity_mean,
            "texture_repetition": avg_similarity,
            "density_entropy": float(entropy),
        }

    def compute_ai_likelihood_score(self, metrics: dict) -> dict:
        """
        Metriklerden AI olma olasılığını hesapla.
        Heuristic skorlar — kalibrasyon test sonuçlarına göre yapılacak.
        """
        score = 0
        signals = []

        # Düşük uniformity_std = uniform dağılım = AI
        if metrics["uniformity_std"] < 0.05:
            score += 30
            signals.append("Edge dağılımı uniform (AI işareti)")
        elif metrics["uniformity_std"] < 0.10:
            score += 15
            signals.append("Edge dağılımı kısmen uniform")

        # Yüksek texture repetition = AI
        if metrics["texture_repetition"] > 0.3:
            score += 30
            signals.append("Tekstür tekrarı yüksek (AI işareti)")
        elif metrics["texture_repetition"] > 0.2:
            score += 15
            signals.append("Tekstür tekrarı orta")

        # Yüksek entropy = uniform dağılım = AI
        if metrics["density_entropy"] > 2.0:
            score += 20
            signals.append("Yoğunluk dağılımı çok düzgün")

        # Çok yüksek edge density (Görsel 4-5 gibi köpük tekstür)
        if metrics["edge_density"] > 0.30:
            score += 20
            signals.append("Aşırı yoğun edge (sentetik doku)")

        return {
            "ai_score": score,
            "max_score": 100,
            "signals": signals,
            "interpretation": (
                "AI olma ihtimali yüksek" if score >= 50 else
                "AI olma ihtimali orta" if score >= 25 else
                "Gerçek fotoğraf görünümü"
            )
        }

    def analyze_all(self, image_path: Path) -> dict:
        """Tüm forensic analizleri yap."""
        ela = self.compute_ela(image_path)
        fft = self.compute_fft_magnitude(image_path)
        edges_array = self.compute_edge_map(image_path)
        edges_image = Image.fromarray(edges_array)

        # Edge pattern analizi (yeni)
        edge_metrics = self.analyze_edge_patterns(edges_array)
        ai_score = self.compute_ai_likelihood_score(edge_metrics)

        # Eski genel metrikler
        ela_arr = np.array(ela.convert("L"))
        fft_arr = np.array(fft)

        h, w = fft_arr.shape
        center_h, center_w = h // 2, w // 2
        center_region = fft_arr[
            center_h - h // 8:center_h + h // 8,
            center_w - w // 8:center_w + w // 8
        ]

        general_metrics = {
            "ela_mean": float(ela_arr.mean()),
            "ela_std": float(ela_arr.std()),
            "fft_center_ratio": float(center_region.mean() / (fft_arr.mean() + 1e-6)),
        }

        # Hepsini birleştir
        all_metrics = {**general_metrics, **edge_metrics}

        return {
            "ela_image": ela,
            "fft_image": fft,
            "edge_image": edges_image,
            "metrics": all_metrics,
            "ai_likelihood": ai_score,
        }
    
    