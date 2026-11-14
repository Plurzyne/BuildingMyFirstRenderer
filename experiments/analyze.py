import numpy as np
import matplotlib.pyplot as plt

WIDTH, HEIGHT = 400, 225


def load(path):
    # Read the raw 32-bit floats written by camera.h and arrange them
    # as rows x columns x 3 colours, the same order as our push_backs.
    data = np.fromfile(path, dtype=np.float32)
    return data.reshape(HEIGHT, WIDTH, 3).astype(np.float64)


def rmse(image, reference):
    return np.sqrt(np.mean((image - reference) ** 2))


SAMPLE_COUNTS = [1, 4, 16, 64, 256]
SEEDS = [1, 2, 3, 4, 5]

reference = load("data/reference.bin")

mean_errors = []
print(f"{'N':>5} {'mean RMSE':>12} {'spread':>8}")

for n in SAMPLE_COUNTS:
    errors = []
    for s in SEEDS:
        image = load(f"data/n{n}_s{s}.bin")
        errors.append(rmse(image, reference))

    mean = np.mean(errors)
    spread = np.std(errors) / mean * 100
    mean_errors.append(mean)
    print(f"{n:>5} {mean:>12.5f} {spread:>7.2f}%")

# --- Fit a straight line on log-log axes ---
log_n = np.log10(SAMPLE_COUNTS)
log_e = np.log10(mean_errors)
slope, intercept = np.polyfit(log_n, log_e, 1)

predicted = slope * log_n + intercept
r_squared = 1 - np.sum((log_e - predicted) ** 2) / np.sum((log_e - np.mean(log_e)) ** 2)

print(f"\nFitted slope: {slope:.4f}   (theory: -0.5)")
print(f"R squared:    {r_squared:.5f}")

# --- Plot ---
n_line = np.array([1, 256])
plt.figure(figsize=(6, 4.5))
plt.loglog(SAMPLE_COUNTS, mean_errors, "o", label="measured (mean of 5 seeds)")
plt.loglog(n_line, 10**intercept * n_line**slope, "-", label=f"fit: slope {slope:.3f}")
plt.loglog(n_line, mean_errors[0] / np.sqrt(n_line), "--", label="theory: slope -0.5")
plt.xlabel("samples per pixel (N)")
plt.ylabel("RMSE against 4096-spp reference")
plt.title("Convergence of BuildingMyFirstRenderer")
plt.legend()
plt.grid(True, which="both", alpha=0.3)
plt.tight_layout()
plt.savefig("convergence.png", dpi=150)
plt.show()
