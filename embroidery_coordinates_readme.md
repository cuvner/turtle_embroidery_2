# Turtle_embroidery


The whole class is built on pyembroidery

# Reliable Embroidery Coordinates in pyembroidery

## Overview
Embroidery viewers and machines have strict expectations for how a design defines its coordinates.
To ensure your designs always appear **centered**, **correctly positioned**, and **machine-safe**, follow these rules.

## 1. Viewer Origin Rules
The PES viewer interprets `(0,0)` as:
- the machine starting point,
- the first JUMP stitch,
- the reference for the bounding box.

### Requirement
✔ First stitch should be a **JUMP at (0,0)**.

## 2. Design Must Live in +X, +Y Quadrant
To appear centered:
- `min_x = 0`
- `min_y = 0`

Any negative coordinates cause viewer shifts.

## 3. Avoid Long Absolute Movements
Large absolute jumps cause:
- clipping,
- unwanted JUMPs,
- distorted shapes.

### Use:
✔ relative stitches  
✔ absolute coordinates **only for logical plotting**

## 4. Reliable Pattern Pipeline
1. Generate all design points logically using absolute coordinates.
2. Collect every point as `(x, y, pen_state)`.
3. Compute:
    - `min_x = min(points.x)`
    - `min_y = min(points.y)`
4. Shift design into +quadrant:
    - `x' = x - min_x`
    - `y' = y - min_y`
5. Start pattern with:
    - `JUMP 0,0`
6. Replay points using relative stitches:
    - `dx = x'[i] - x'[i-1]`
    - `dy = y'[i] - y'[i-1]`
7. End with:
    - `END`

## 5. Why This Works
This matches PES format expectations:
- start at origin,
- positive quadrant only,
- short relative stitches,
- no complex transforms.

## 6. Example Workflow Summary
### Good
- shift to +quadrant,
- relative stitches,
- JUMP(0,0),
- END.

### Bad
- negative coordinates,
- long absolute jumps,
- post-stitch centering.

## 7. Bounding Box Formulas
```
min_x = min(all_points.x)
min_y = min(all_points.y)
max_x = max(all_points.x)
max_y = max(all_points.y)
```
Shift:
```
x' = x - min_x
y' = y - min_y
```
Relative stitch:
```
dx = x'[i] - x'[i-1]
dy = y'[i] - y'[i-1]
```

## 8. Summary
✔ Start at `(0,0)`  
✔ Shift so `min_x = min_y = 0`  
✔ Use only relative stitches  
✔ No long absolute jumps  
✔ Never use negative coordinates  
✔ This matches the behavior of square_clean.py  

