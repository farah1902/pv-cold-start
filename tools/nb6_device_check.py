"""Device check without a GPU (D80 extension, 24 Nov 2026), run locally before each GPU mirror:

    python tools/nb6_device_check.py [ROW ...]          # default: every GPU row of tools/nb6_gpu.py

During one real training step of every GPU row's model on the CPU (forward with donor dropout, loss with the horizon
weights, backward, optimiser step, then an eval forward, as setformer._train and _predict do), it records every tensor
constructor called from our model files (src/pvcold/setformer.py, timexer.py) without a device argument. On a GPU
such a tensor is made on the CPU and meets CUDA tensors: the TimeXer failure of 24 Nov (timexer.py line 95), which
this check finds on that code. torch's own modules pass devices themselves. Writes results/nb6_device_check/.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "tools"))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402
from torch.overrides import TorchFunctionMode  # noqa: E402
from torch.utils._device import _device_constructors  # noqa: E402

import nb6_forecast as NF  # noqa: E402
import nb6_gpu as G  # noqa: E402
from pvcold import audit as A_  # noqa: E402
from pvcold import forecast as FC  # noqa: E402
from pvcold import setformer as SF  # noqa: E402

OURS = ("setformer.py", "timexer.py")
CTORS = _device_constructors()


class Watch(TorchFunctionMode):
    """Records constructors called from our model files without a device."""

    def __init__(self):
        super().__init__()
        self.hits = set()

    def __torch_function__(self, func, types, args=(), kwargs=None):
        kwargs = kwargs or {}
        if func in CTORS and kwargs.get("device") is None:
            f = sys._getframe(1)
            while f and "/torch/" in f.f_code.co_filename.replace("\\", "/"):
                f = f.f_back                                  # skip torch's own frames
            if f and f.f_code.co_filename.endswith(OURS):
                self.hits.add(f"{Path(f.f_code.co_filename).name}:{f.f_lineno} {func.__name__}")
        return func(*args, **kwargs)


def main():
    fz, _, _ = NF.frozen()
    rows = sys.argv[1:] or list(G.GPU_ROWS)
    rec = []
    for row in rows:
        I, cfg, seeds, mk = G.row_setup(row, fz)
        A = mk(I.EVENTS[0])
        issue, Y, M = SF.targets(A)
        idx = np.where(issue & M.any(1) & (np.arange(len(A["S"].index)) >= SF.L - 1))[0][:64]
        B = SF.samples(A, idx)
        torch.manual_seed(0)
        model = SF.build_model(cfg)                  # built outside the watch: parameters and buffers follow .to()
        xb = SF._tensors(B)
        taus = torch.tensor(FC.TAUS, dtype=torch.float32)
        y = torch.from_numpy(np.nan_to_num(Y[idx]).astype(np.float32))
        m = torch.from_numpy(M[idx].astype(np.float32))
        w = torch.ones(len(FC.H))
        opt = torch.optim.AdamW(model.parameters(), lr=cfg["lr"], weight_decay=cfg["weight_decay"])
        W = Watch()
        with W:
            model.train()
            keep = torch.rand(xb[2].shape, device="cpu") >= cfg["donor_dropout"]
            xb2 = list(xb)
            xb2[2] = xb[2] & keep
            loss = SF._loss(model(*xb2), y, m, taus, w)
            loss.backward()
            opt.step()
            model.eval()
            with torch.no_grad():
                model(*xb)
        rec.append({"row": row, "arch": cfg.get("arch"), "summary_only": cfg["summary_only"], "ext": cfg["ext"],
                    "constructors_without_device": "; ".join(sorted(W.hits))})
        print(f"{row} ({cfg.get('arch')}, summary_only {cfg['summary_only']}, ext '{cfg['ext']}'): "
              f"constructors without a device in our model code: {sorted(W.hits) or 'none'}", flush=True)
    R = pd.DataFrame(rec)
    passed = bool((R["constructors_without_device"] == "").all())
    print("DEVICE CHECK", "PASSED" if passed else "FAILED")
    if len(rows) == len(G.GPU_ROWS):                 # the record covers every GPU row
        out = A_.write_outputs("nb6_device_check", {"rows": R},
                               {"tool": "nb6_device_check", "decision": "D80 (extension)", "environment": A_.versions(),
                                "passed": passed, "rows": rows, "code_sha256": G.code_sha(),
                                "commit": NF.git("rev-parse", "HEAD")})
        print("written to", out)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
