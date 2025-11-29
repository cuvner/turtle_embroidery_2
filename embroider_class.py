import math
from pyembroidery import (
    EmbPattern,
    EmbThread,
    STITCH,
    JUMP,
    END,
    write_pes,
    write_svg,
)


class TurtleEmbroidery:
    """
    Turtle-like drawing interface for pyembroidery.

    Behaviour:
    - All motion is first recorded as logical points (x, y, pen_down).
    - On finish(), points are shifted so min_x = 0 and min_y = 0.
    - Output pattern starts with a JUMP at (0, 0).
    - All stitching is done with *relative* stitches/jumps,
      just like your working square_clean.py example.
    - No extra centering or transforms after that.
    """

    def __init__(self, color="#00ff00", step=2.0):
        """
        color: initial thread colour (hex string).
        step:  maximum length of each stitched step when using forward()/goto().
        """
        self.color = color
        self.step = float(step)

        # logical state
        self.x = 0.0
        self.y = 0.0
        self.heading = 0.0
        self.pen_down = True

        # record of points: list of (x, y, pen_down)
        self.points = []

    # ---------- logical movement (no stitches yet) ----------

    def _record_point(self):
        """Record current position and pen state."""
        self.points.append((self.x, self.y, self.pen_down))

    def _step_relative_logic(self, dx, dy):
        """Update logical position by (dx, dy) and record."""
        self.x += float(dx)
        self.y += float(dy)
        self._record_point()

    def _move_to_logic(self, x, y):
        """Move logically to absolute (x, y) using step-sized increments if pen is down."""
        dx = x - self.x
        dy = y - self.y

        if self.pen_down:
            dist = math.hypot(dx, dy)
            if dist == 0:
                return
            steps = max(1, int(dist / self.step))
            sdx = dx / steps
            sdy = dy / steps
            for _ in range(steps):
                self._step_relative_logic(sdx, sdy)
        else:
            self._step_relative_logic(dx, dy)

    # ---------- turtle-like API ----------

    def forward(self, distance):
        """Move forward in the current heading, logically."""
        if distance == 0:
            return

        steps = max(1, int(abs(distance) / self.step))
        step_len = distance / steps
        ang = math.radians(self.heading)
        dx = math.cos(ang) * step_len
        dy = math.sin(ang) * step_len

        for _ in range(steps):
            self._step_relative_logic(dx, dy)

    def back(self, distance):
        self.forward(-distance)

    def left(self, angle):
        self.heading += float(angle)

    def right(self, angle):
        self.heading -= float(angle)

    def penup(self):
        self.pen_down = False

    def pendown(self):
        self.pen_down = True

    def goto(self, x, y):
        """Logical absolute move; will be turned into relative stitches later."""
        self._move_to_logic(float(x), float(y))

    def setheading(self, angle):
        self.heading = float(angle)

    # (you can add color changes later if needed; for now single colour like square_clean.py)

    # ---------- simple shapes ----------

    def draw_square(self, size):
        for _ in range(4):
            self.forward(size)
            self.left(90)

    def draw_spiro(self, R, r, d, revolutions=6, step_deg=3):
        """
        Draw a Spirograph-style hypotrochoid, then later we shift it into +x,+y.
        """
        self.penup()
        first = True

        for angle in range(0, int(360 * revolutions) + 1, step_deg):
            t = math.radians(angle)
            k = (R - r) / r

            x = (R - r) * math.cos(t) + d * math.cos(k * t)
            y = (R - r) * math.sin(t) - d * math.sin(k * t)

            if first:
                self.goto(x, y)
                self.pendown()
                first = False
            else:
                self.goto(x, y)

        self.penup()

    # ---------- build EmbPattern in square_clean style ----------

    def finish(self) -> EmbPattern:
        """
        Build and return an EmbPattern that:
        - has one thread colour,
        - starts with JUMP at (0,0),
        - contains only relative stitches/jumps,
        - all coordinates are in the +x,+y quadrant (min_x = 0, min_y = 0),
        - ends with END.
        """
        pattern = EmbPattern()
        pattern.add_thread(EmbThread(self.color))

        if not self.points:
            pattern.add_command(END)
            return pattern

        # 1) shift points so min_x = 0, min_y = 0
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        min_x = min(xs)
        min_y = min(ys)

        shifted = [(x - min_x, y - min_y, pen) for (x, y, pen) in self.points]

        # 2) start at (0,0) with a JUMP (like square_clean.py)
        pattern.add_stitch_absolute(JUMP, 0, 0)
        prev_x, prev_y = 0.0, 0.0

        # 3) replay shifted points as relative moves
        for (x, y, pen) in shifted:
            dx = x - prev_x
            dy = y - prev_y
            cmd = STITCH if pen else JUMP
            pattern.add_stitch_relative(cmd, dx, dy)
            prev_x, prev_y = x, y

        # 4) END
        pattern.add_command(END)
        return pattern


# ---------- demo / quick test ----------

def main():
    t = TurtleEmbroidery(color="#00ff00", step=1.5)

    # Example: spirograph that will be treated exactly like your centred square
    t.draw_square(40)

    pattern = t.finish()

    write_pes(pattern, "turtle_spiro_clean.pes")
    write_svg(pattern, "turtle_spiro_clean.svg")
    print("Wrote turtle_spiro_clean.pes and turtle_spiro_clean.svg")


if __name__ == "__main__":
    main()
