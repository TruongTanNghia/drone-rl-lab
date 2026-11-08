// Đọc tay cầm USB (Gamepad API) hoặc bàn phím thành 4 kênh: ga, yaw, pitch, roll.
// Mode 2 (phổ biến): cần trái = ga + yaw, cần phải = pitch + roll. Mode 1: đổi ga ↔ pitch.

import type { Inputs } from "./drone";

export type StickMode = 1 | 2;
export type InputCfg = {
  mode: StickMode;
  deadzone: number;
  expo: number; // 0 = tuyến tính, 0.5 = mềm quanh giữa
  invert: { thr: boolean; yaw: boolean; pitch: boolean; roll: boolean };
  axes: { lx: number; ly: number; rx: number; ry: number }; // chỉ số trục trên tay cầm
};

export const DEFAULT_CFG: InputCfg = { mode: 2, deadzone: 0.06, expo: 0.3, invert: { thr: false, yaw: false, pitch: false, roll: false }, axes: { lx: 0, ly: 1, rx: 2, ry: 3 } };

const KEY = "drone-trainer.input";

export function loadCfg(): InputCfg {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return { ...DEFAULT_CFG, ...JSON.parse(raw) };
  } catch {
    /* bỏ qua */
  }
  return DEFAULT_CFG;
}

export function saveCfg(c: InputCfg) {
  try {
    localStorage.setItem(KEY, JSON.stringify(c));
  } catch {
    /* bỏ qua */
  }
}

function shape(v: number, dz: number, expo: number): number {
  const a = Math.abs(v);
  if (a < dz) return 0;
  const n = Math.min(1, (a - dz) / (1 - dz));
  const e = (1 - expo) * n + expo * n * n * n;
  return Math.sign(v) * e;
}

export type GamepadRead = { u: Inputs; raw: number[]; id: string };

/** Đọc tay cầm đầu tiên đang kết nối; null nếu không có. */
export function readGamepad(cfg: InputCfg): GamepadRead | null {
  if (typeof navigator === "undefined" || !navigator.getGamepads) return null;
  const pads = navigator.getGamepads();
  let gp: Gamepad | null = null;
  for (const p of pads) if (p && p.connected) {
    gp = p;
    break;
  }
  if (!gp) return null;
  const ax = (i: number) => (i < gp!.axes.length ? gp!.axes[i] : 0);
  const lx = ax(cfg.axes.lx), ly = ax(cfg.axes.ly), rx = ax(cfg.axes.rx), ry = ax(cfg.axes.ry);
  // trục dọc tay cầm: đẩy lên = −1 → đổi dấu để "lên" là dương
  let thr: number, yaw: number, pitch: number, roll: number;
  if (cfg.mode === 2) {
    thr = -ly;
    yaw = lx;
    pitch = -ry;
    roll = rx;
  } else {
    thr = -ry;
    yaw = lx;
    pitch = -ly;
    roll = rx;
  }
  const inv = cfg.invert;
  const u: Inputs = {
    thr: shape(inv.thr ? -thr : thr, cfg.deadzone, cfg.expo),
    yaw: shape(inv.yaw ? -yaw : yaw, cfg.deadzone, cfg.expo),
    pitch: shape(inv.pitch ? -pitch : pitch, cfg.deadzone, cfg.expo),
    roll: shape(inv.roll ? -roll : roll, cfg.deadzone, cfg.expo),
  };
  return { u, raw: Array.from(gp.axes), id: gp.id };
}

/** Bàn phím giả lập cần: W/S ga, A/D yaw, mũi tên pitch/roll. Giá trị trượt dần như cần thật. */
export class KeyInput {
  private down = new Set<string>();
  private cur: Inputs = { thr: 0, yaw: 0, pitch: 0, roll: 0 };
  private onDown = (e: KeyboardEvent) => {
    if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", " "].includes(e.key)) e.preventDefault();
    this.down.add(e.key.length === 1 ? e.key.toLowerCase() : e.key);
  };
  private onUp = (e: KeyboardEvent) => this.down.delete(e.key.length === 1 ? e.key.toLowerCase() : e.key);
  private onBlur = () => this.down.clear();
  attach() {
    window.addEventListener("keydown", this.onDown);
    window.addEventListener("keyup", this.onUp);
    window.addEventListener("blur", this.onBlur);
  }
  detach() {
    window.removeEventListener("keydown", this.onDown);
    window.removeEventListener("keyup", this.onUp);
    window.removeEventListener("blur", this.onBlur);
  }
  get active(): boolean {
    return this.down.size > 0 || Math.abs(this.cur.thr) + Math.abs(this.cur.yaw) + Math.abs(this.cur.pitch) + Math.abs(this.cur.roll) > 0.01;
  }
  read(dt: number): Inputs {
    const d = this.down;
    const tgt: Inputs = {
      thr: (d.has("w") ? 1 : 0) - (d.has("s") ? 1 : 0),
      yaw: (d.has("d") ? 1 : 0) - (d.has("a") ? 1 : 0),
      pitch: (d.has("ArrowUp") ? 1 : 0) - (d.has("ArrowDown") ? 1 : 0),
      roll: (d.has("ArrowRight") ? 1 : 0) - (d.has("ArrowLeft") ? 1 : 0),
    };
    const rate = 3.5; // cần đi hết hành trình trong ~0.3 s
    const slew = (c: number, t: number) => c + Math.max(-rate * dt, Math.min(rate * dt, t * 0.7 - c));
    this.cur = { thr: slew(this.cur.thr, tgt.thr), yaw: slew(this.cur.yaw, tgt.yaw), pitch: slew(this.cur.pitch, tgt.pitch), roll: slew(this.cur.roll, tgt.roll) };
    return { ...this.cur };
  }
}
