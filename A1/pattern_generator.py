# -------- Assignment 1: 2D Pattern Generation with NumPy --------

# Import of libraries
import numpy as np
import matplotlib.pyplot as plt

# Canvas resolution kept small to emphasize structure
h, w = 100, 100

# Coordinate grid for vectorized spatial operations
rows = np.arange(h)
cols = np.arange(w)
X, Y = np.meshgrid(cols, rows)

# Center point defines radial symmetry
cy, cx = h // 2, w // 2

# Distance from center used to create a smooth base pattern
dist = np.sqrt((X - cx)**2 + (Y - cy)**2)

# Add a small sine variation to make the gradient more visually appealing
gradient = np.sqrt(dist) / 6
gradient += 0.25 * np.sin(dist * 0.4)

# Hard outer border frames the composition
gradient[0, :] = gradient.min()
gradient[-1, :] = gradient.min()
gradient[:, 0] = gradient.min()
gradient[:, -1] = gradient.min()

# Center rectangle
gradient[cy-5, cx-5:cx+5] = gradient.max()
gradient[cy+5, cx-5:cx+5] = gradient.max()
gradient[cy-5:cy+6, cx-5] = gradient.max()
gradient[cy-5:cy+6, cx+5] = gradient.max()

# Normalize for stable color mapping
canvas_n = (gradient - gradient.min()) / (gradient.max() - gradient.min())

# Adjust brightness to make transitions smoother
canvas_n = canvas_n ** 0.85

# Minimal noise adds texture without visual clutter
noise = np.random.uniform(-0.01, 0.01, (h, w))
canvas_n += noise * (dist / dist.max())

# Limited three-color palette to enforce visual restraint
c1 = np.array([0.95, 0.85, 0.20])   # warm yellow
c2 = np.array([0.20, 0.70, 0.85])   # cyan
c3 = np.array([0.55, 0.20, 0.75])   # purple

# Gradually blend between the three colors
w1 = np.clip(1 - canvas_n * 2, 0, 1)
w2 = np.clip(1 - np.abs(canvas_n - 0.5) * 2, 0, 1)
w3 = np.clip(canvas_n * 2 - 1, 0, 1)

# Note: The above lines smoothly distribute each pixel’s value between three colors based on its intensity

# Final color image from weighted palette blending
canvas_rgb = (
    w1[..., None] * c1 +
    w2[..., None] * c2 +
    w3[..., None] * c3
)

# Attractors add subtle local variation without overpowering structure
attractors = np.random.randint(0, h, size=(4, 2))
R = 15

for ax, ay in attractors:
    d = np.sqrt((X - ax)**2 + (Y - ay)**2) # distance function
    mask = d < R # limits radius of influence
    shift = 0.1 * np.sin(d * 0.5) # creates a smooth brightness variation based on distance from the attractor
    canvas_rgb[mask] += shift[mask, None] # application of variation based on distance from attractor

# Clamp values to valid RGB range
canvas_rgb = np.clip(canvas_rgb, 0, 1)

# Display result
plt.imshow(canvas_rgb)
plt.axis('off')
plt.title("Unique pattern")
plt.show()