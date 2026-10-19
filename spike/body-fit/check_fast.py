"""Check the fast (optimiser) measurer against the exact one on random bodies."""
import time, numpy as np
from body import Body
b = Body()
rng = np.random.default_rng(0)
Z = ["chest","waist","hip","thigh","inseam"]
for sex in [0.0, 1.0]:
    b.landmark_ids(sex)
    diffs, tf = [], []
    for k in range(10):
        pheno = dict(gender=sex, muscle=rng.uniform(0.1,0.9), weight=rng.uniform(0.05,0.95), height=rng.uniform(0.1,0.9), proportions=rng.uniform(0,1))
        local = {"measure-bust-circ-incr": rng.uniform(-0.6,0.6), "measure-waist-circ-incr": rng.uniform(-0.6,0.6), "measure-hips-circ-incr": rng.uniform(-0.6,0.6), "stomach-pregnant-incr": rng.uniform(0,0.5)}
        v, j = b.build(pheno, local)
        slow, _ = b.measure(v, j)
        t=time.time(); fast = b.quick_measure(v, j, sex); tf.append(time.time()-t)
        diffs.append([fast[k]-slow[k] for k in Z])
    d = np.array(diffs)
    print(f"sex {sex}: fast {np.mean(tf)*1000:.0f} ms; max |diff| cm", dict(zip(Z, np.abs(d).max(0).round(2))), "mean diff", dict(zip(Z, d.mean(0).round(2))))
