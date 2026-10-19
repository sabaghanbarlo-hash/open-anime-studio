"""Organic motion for one character: springs, random blinks, speech-driven nods/gestures.
Everything is eased and slightly randomised so it never loops or looks mechanical."""
import math, random


class Spring:
    def __init__(self, k=40.0, zeta=0.75):
        self.x = self.v = self.t = 0.0
        self.k, self.c = k, 2 * zeta * math.sqrt(k)

    def step(self, dt):
        a = self.k * (self.t - self.x) - self.c * self.v
        self.v += a * dt
        self.x += self.v * dt
        return self.x


class Rig:
    def __init__(self, seed=0):
        self.r = random.Random(seed)
        self.ph = [self.r.uniform(0, 6.28) for _ in range(8)]
        self.tilt, self.nod = Spring(35), Spring(45)
        self.brow, self.gest, self.look = Spring(70), Spring(28, 0.55), Spring(20)
        self.t = 0.0
        self.mouth = 0.0
        self.next_blink = self.r.uniform(1.0, 3.0)
        self.blink_t = -1.0
        self.gest_cool = self.r.uniform(0.5, 1.5)
        self.gest_hold = 0.0
        self.gstyle = 0.5
        self.env_prev = 0.0
        self.hold_look = 0.0

    def update(self, dt, env, speaking):
        self.t += dt
        t, ph = self.t, self.ph
        e = env if speaking else 0.0

        # idle sway (never exactly repeats: incommensurate frequencies)
        self.tilt.t = 1.3 * math.sin(t * 0.61 + ph[0]) + 0.7 * math.sin(t * 1.37 + ph[1]) + 2.2 * e * math.sin(t * 2.1 + ph[2])
        self.nod.t = 1.5 * math.sin(t * 0.93 + ph[3]) + 5.0 * e
        self.brow.t = 1.0 if (speaking and e > 0.62) else 0.0

        # slow eye wander
        self.hold_look -= dt
        if self.hold_look <= 0:
            self.look.t = self.r.uniform(-1, 1) * (0.5 if speaking else 1.0)
            self.hold_look = self.r.uniform(0.8, 2.5)

        # lip sync: fast attack, slower release
        k = 38 if e > self.mouth else 20
        self.mouth += (e - self.mouth) * (1 - math.exp(-dt * k))

        # gestures on emphasis peaks
        self.gest_cool -= dt
        if speaking and e > 0.5 and e > self.env_prev and self.gest_cool <= 0 and self.r.random() < 0.5:
            self.gest.t = self.r.uniform(0.7, 1.0)
            self.gest_hold = self.r.uniform(0.45, 0.9)
            self.gest_cool = self.r.uniform(1.3, 3.0)
            self.gstyle = self.r.random()
        if self.gest_hold > 0:
            self.gest_hold -= dt
        else:
            self.gest.t = 0.12 if speaking else 0.0
        self.env_prev = e

        # blinks (sometimes double)
        blink = 0.0
        if self.blink_t < 0 and t > self.next_blink:
            self.blink_t = 0.0
        if self.blink_t >= 0:
            self.blink_t += dt
            dur = 0.17
            blink = math.sin(math.pi * min(self.blink_t / dur, 1.0))
            if self.blink_t > dur:
                self.blink_t = -1.0
                self.next_blink = t + (0.15 if self.r.random() < 0.15 else self.r.uniform(2.0, 5.0))

        return dict(
            tilt=self.tilt.step(dt), nod=self.nod.step(dt), brow=self.brow.step(dt),
            gest=max(0.0, self.gest.step(dt)), gstyle=self.gstyle, look=self.look.step(dt),
            mouth=max(0.0, min(1.0, self.mouth)), blink=blink,
            breath=math.sin(t * 1.5 + ph[4]),
        )
