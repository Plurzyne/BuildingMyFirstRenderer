import numpy as np
import matplotlib.pyplot as plt

WIDTH, HEIGHT = 400, 225
SAMPLE_COUNTS = [1, 4, 16, 64, 256]
SEEDS = [1, 2, 3, 4, 5]
REGIONS = {
    1: "Ground (Lambertian)",
    2: "Centre (Lambertian)",
    3: "Glass (dielectric)",
    4: "Metal (fuzz = 1.0)",
    0: "Background (sky)",
}

def load(path):
    data = np.fromfile(path, dtype=np.float32)
    return data.reshape(HEIGHT, WIDTH, 3).astype(np.float64)

def erode(mask, radius=3):
    # Keep a pixel only if every pixel in the square around it
    # (7 x 7 for radius 3) is also in the mask.
    padded = np.pad(mask, radius, constant_values=False)
    result = np.ones_like(mask)
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            result &= padded[radius + dy : radius + dy + HEIGHT,
                             radius + dx : radius + dx + WIDTH]
    return result

ids = np.fromfile("data/ids.bin", dtype=np.uint8).reshape(HEIGHT, WIDTH)
reference = load("data/reference.bin")

header = f"{'Region':<22}{'pixels':>7}"
for n in SAMPLE_COUNTS:
    header += f"{n:>9}"
header += f"{'slope':>8}{'C':>9}"
print(header)

plt.figure(figsize=(6.5, 4.5))

for region_id, name in REGIONS.items():
    mask = erode(ids == region_id)

    errors = []
    for n in SAMPLE_COUNTS:
        per_seed = []
        for s in SEEDS:
            image = load(f"data/n{n}_s{s}.bin")
            per_seed.append(np.sqrt(np.mean((image[mask] - reference[mask]) ** 2)))
        errors.append(np.mean(per_seed))

    slope, intercept = np.polyfit(np.log10(SAMPLE_COUNTS), np.log10(errors), 1)
    C = 10 ** intercept

    row = f"{name:<22}{mask.sum():>7}"
    for e in errors:
        row += f"{e:>9.5f}"
    row += f"{slope:>8.3f}{C:>9.4f}"
    print(row)

    plt.loglog(SAMPLE_COUNTS, errors, "o-", label=name)

plt.xlabel("samples per pixel (N)")
plt.ylabel("RMSE against 4096-spp reference")
plt.title("Convergence by material")
plt.legend(fontsize=8)
plt.grid(True, which="both", alpha=0.3)
plt.tight_layout()
plt.savefig("convergence_by_material.png", dpi=150)
plt.show()